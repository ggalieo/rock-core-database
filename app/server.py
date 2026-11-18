# -*- coding: utf-8 -*-
"""Tiny local API + static server for the core database demo."""
import argparse
import json
import mimetypes
import os
import re
import sqlite3
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
DB_PATH = BASE / "data" / "core.db"
PORT = int(os.environ.get("PORT", "8010"))


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def ok(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def fail(handler, msg, status=400):
    ok(handler, {"error": msg}, status)


def image_url(file):
    return "/" + file.replace("\\", "/") if file else ""


def enrich_images(conn, items):
    for it in items:
        it["url"] = image_url(it.get("file", ""))
        it["thumb_url"] = image_url(it.get("thumb", ""))
    return items


# ---------------------------------------------------------------- APIs
def api_overview(conn):
    meta = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM meta")}
    kpi = {
        "inventory_m": float(meta.get("inventory_m", 0)),
        "cuttings_bags": int(float(meta.get("cuttings_bags", 0))),
        "sidewall_pcs": int(float(meta.get("sidewall_pcs", 0))),
        "coverage": float(meta.get("coverage", 0)),
        "scanned_m": float(meta.get("scanned_m", 0)),
        "total_wells": int(float(meta.get("total_wells", 0))),
        "images": int(float(meta.get("images", 0))),
        "today_scans": int(float(meta.get("today_scans", 0))),
        "updated_at": meta.get("updated_at", ""),
    }
    scan_by_well = rows(conn, """SELECT code, name, scanned AS value FROM wells
        WHERE scanned > 0 ORDER BY scanned DESC LIMIT 7""")
    latest = rows(conn, """SELECT s.id, s.top_md, s.bottom_md, s.scanned_at, s.images_count,
        w.id AS well_id, w.code, w.name,
        (SELECT i.id FROM images i WHERE i.well_id=w.id AND i.type='SURFACE' ORDER BY i.id LIMIT 1) AS image_id
        FROM scans s JOIN wells w ON w.id=s.well_id ORDER BY s.scanned_at DESC LIMIT 6""")
    for it in latest:
        it["thumb_url"] = f"/assets/core/thumb_{it['image_id']}.jpg" if it["image_id"] else ""
    map_points = rows(conn, """SELECT id, code, name, region, lon, lat, coverage, inventory
        FROM wells ORDER BY id""")
    todos = {
        "pending": one(conn, "SELECT COUNT(*) c FROM wells WHERE status='待扫描'")["c"],
        "partial": one(conn, "SELECT COUNT(*) c FROM wells WHERE status='部分扫描'")["c"],
        "missing": one(conn, "SELECT COUNT(*) c FROM wells WHERE coverage=0")["c"],
        "annotations": one(conn, "SELECT COUNT(*) c FROM annotations")["c"],
    }
    return {
        "kpi": kpi,
        "scan_by_well": scan_by_well,
        "cuttings_by_region": json.loads(meta.get("cuttings_by_region", "[]")),
        "inventory_by_region": json.loads(meta.get("inventory_by_region", "[]")),
        "latest": latest,
        "map_points": map_points,
        "todos": todos,
    }


def api_wells(conn, qs):
    q = (qs.get("q", [""])[0] or "").strip()
    region = qs.get("region", [""])[0]
    year = qs.get("year", [""])[0]
    tectonic = qs.get("tectonic", [""])[0]
    page = max(1, int(qs.get("page", ["1"])[0] or 1))
    size = min(50, max(1, int(qs.get("page_size", ["10"])[0] or 10)))
    where, params = ["1=1"], []
    if q:
        where.append("(code LIKE ? OR name LIKE ? OR region LIKE ?)")
        params += [f"%{q}%"] * 3
    if region:
        where.append("region = ?"); params.append(region)
    if year:
        where.append("year = ?"); params.append(int(year))
    if tectonic:
        where.append("tectonic = ?"); params.append(tectonic)
    wsql = " AND ".join(where)
    total = one(conn, f"SELECT COUNT(*) c FROM wells WHERE {wsql}", params)["c"]
    items = rows(conn, f"""SELECT * FROM wells WHERE {wsql}
        ORDER BY (status='已扫描') DESC, id ASC LIMIT ? OFFSET ?""",
                 params + [size, (page - 1) * size])
    for it in items:
        prods = rows(conn, "SELECT code, status FROM products WHERE well_id=?", (it["id"],))
        it["products"] = {p["code"]: p["status"] for p in prods}
    filters = {
        "regions": [r["region"] for r in conn.execute("SELECT DISTINCT region FROM wells ORDER BY region")],
        "years": [r["year"] for r in conn.execute("SELECT DISTINCT year FROM wells ORDER BY year DESC")],
        "tectonics": [r["tectonic"] for r in conn.execute("SELECT DISTINCT tectonic FROM wells ORDER BY tectonic")],
    }
    return {"items": items, "total": total, "page": page, "page_size": size, "filters": filters}


def api_well_detail(conn, wid):
    well = one(conn, "SELECT * FROM wells WHERE id=?", (wid,))
    if not well:
        return None
    runs = rows(conn, "SELECT * FROM runs WHERE well_id=? ORDER BY run_no", (wid,))
    for run in runs:
        secs = rows(conn, "SELECT * FROM sections WHERE run_id=? ORDER BY section_no", (run["id"],))
        for s in secs:
            img = one(conn, """SELECT id, file, thumb FROM images WHERE section_id=? AND type='SURFACE'
                ORDER BY id LIMIT 1""", (s["id"],))
            s["image_id"] = img["id"] if img else None
            s["image_url"] = image_url(img["file"]) if img else ""
            s["strip_url"] = image_url(s.get("strip_file", ""))
        run["sections"] = secs
        run["strata"] = rows(conn, "SELECT * FROM strata WHERE run_id=? ORDER BY top_md", (run["id"],))
        for typ in ("ROLLED", "FLUORESCENCE"):
            img = one(conn, "SELECT id, file, thumb FROM images WHERE run_id=? AND type=? ORDER BY id LIMIT 1",
                      (run["id"], typ))
            run[typ.lower()] = {"id": img["id"], "url": image_url(img["file"]), "thumb": image_url(img["thumb"]),
                                "vertical": image_url(img["file"].replace(".jpg", "_v.jpg"))} if img else None
    images = enrich_images(conn, rows(conn, """SELECT i.*, s.section_no, r.run_no FROM images i
        LEFT JOIN sections s ON s.id=i.section_id LEFT JOIN runs r ON r.id=i.run_id
        WHERE i.well_id=? ORDER BY i.top_md, i.type""", (wid,)))
    experiments = rows(conn, "SELECT * FROM experiments WHERE well_id=? ORDER BY id", (wid,))
    inventory = rows(conn, """SELECT inv.*, s.section_no, s.top_md, s.bottom_md FROM inventory inv
        LEFT JOIN sections s ON s.id=inv.section_id WHERE inv.well_id=? ORDER BY inv.id""", (wid,))
    prods = {p["code"]: p["status"] for p in conn.execute("SELECT code,status FROM products WHERE well_id=?", (wid,))}
    return {"well": well, "runs": runs, "images": images, "experiments": experiments,
            "inventory": inventory, "products": prods}


def api_image_detail(conn, iid):
    img = one(conn, """SELECT i.*, w.code, w.name, w.region, w.tectonic,
        r.run_no, r.layer, s.section_no, s.oil_show, s.fluorescence, s.rqd,
        s.lithology, s.description, s.color
        FROM images i JOIN wells w ON w.id=i.well_id
        LEFT JOIN runs r ON r.id=i.run_id LEFT JOIN sections s ON s.id=i.section_id
        WHERE i.id=?""", (iid,))
    if not img:
        return None
    img["url"] = image_url(img["file"])
    img["thumb_url"] = image_url(img["thumb"])
    siblings = enrich_images(conn, rows(conn, """SELECT i.*, s.section_no, r.run_no FROM images i
        LEFT JOIN sections s ON s.id=i.section_id LEFT JOIN runs r ON r.id=i.run_id
        WHERE i.well_id=? AND (i.run_id=? OR i.section_id=?)
        ORDER BY i.top_md, i.type""", (img["well_id"], img["run_id"], img["section_id"])))
    annotations = rows(conn, "SELECT * FROM annotations WHERE image_id=? ORDER BY id", (iid,))
    for a in annotations:
        try:
            a["geometry"] = json.loads(a["geometry"])
        except Exception:
            pass
    # prev/next by depth within same run
    prev_img = one(conn, """SELECT id, top_md FROM images WHERE run_id=? AND top_md < ? ORDER BY top_md DESC, id LIMIT 1""",
                   (img["run_id"], img["top_md"])) if img["run_id"] else None
    next_img = one(conn, """SELECT id, top_md FROM images WHERE run_id=? AND top_md > ? ORDER BY top_md ASC, id LIMIT 1""",
                   (img["run_id"], img["top_md"])) if img["run_id"] else None
    return {"image": img, "siblings": siblings, "annotations": annotations,
            "prev": prev_img, "next": next_img}


def api_search(conn, qs):
    q = (qs.get("q", [""])[0] or "").strip()
    if not q:
        return {"q": q, "wells": [], "sections": [], "images": []}
    like = f"%{q}%"
    wells = rows(conn, "SELECT * FROM wells WHERE code LIKE ? OR name LIKE ? OR region LIKE ? OR tectonic LIKE ? LIMIT 12",
                 (like, like, like, like))
    sections = rows(conn, """SELECT s.*, w.code, w.name,
        (SELECT i.thumb FROM images i WHERE i.section_id=s.id AND i.type='SURFACE' ORDER BY i.id LIMIT 1) AS thumb
        FROM sections s JOIN wells w ON w.id=s.well_id
        WHERE s.lithology LIKE ? OR s.description LIKE ? OR s.section_no LIKE ? OR s.oil_show LIKE ?
        ORDER BY s.id LIMIT 20""", (like, like, like, like))
    images = enrich_images(conn, rows(conn, """SELECT i.*, w.code, w.name FROM images i JOIN wells w ON w.id=i.well_id
        WHERE i.type LIKE ? OR w.code LIKE ? OR w.name LIKE ? ORDER BY i.id LIMIT 12""",
                                     (like, like, like)))
    return {"q": q, "wells": wells, "sections": sections, "images": images}


def api_stats(conn):
    region = rows(conn, """SELECT region, COUNT(*) wells, ROUND(AVG(coverage),1) coverage,
        ROUND(SUM(inventory),1) inventory FROM wells GROUP BY region ORDER BY inventory DESC""")
    lith = rows(conn, "SELECT lithology, COUNT(*) c FROM sections GROUP BY lithology ORDER BY c DESC")
    exp = rows(conn, "SELECT test_type, COUNT(*) c FROM experiments GROUP BY test_type ORDER BY c DESC")
    inv = rows(conn, "SELECT status, COUNT(*) c FROM inventory GROUP BY status")
    years = rows(conn, "SELECT substr(scanned_at,1,4) y, COUNT(*) c FROM scans GROUP BY y ORDER BY y")
    return {"region": region, "lith": lith, "exp": exp, "inv": inv, "years": years}


def api_inventory(conn, qs):
    status = qs.get("status", [""])[0]
    where, params = ["1=1"], []
    if status:
        where.append("inv.status=?"); params.append(status)
    items = rows(conn, f"""SELECT inv.*, w.code, w.name, s.section_no, s.top_md, s.bottom_md
        FROM inventory inv JOIN wells w ON w.id=inv.well_id LEFT JOIN sections s ON s.id=inv.section_id
        WHERE {' AND '.join(where)} ORDER BY inv.id LIMIT 60""", params)
    summary = rows(conn, "SELECT status, COUNT(*) c, ROUND(SUM(quantity),2) q FROM inventory GROUP BY status")
    locations = rows(conn, "SELECT location, COUNT(*) c FROM inventory GROUP BY location ORDER BY c DESC LIMIT 12")
    return {"items": items, "summary": summary, "locations": locations}


def api_admin(conn):
    return {
        "users": rows(conn, "SELECT * FROM users ORDER BY id"),
        "audit": rows(conn, "SELECT * FROM audit ORDER BY id DESC LIMIT 12"),
        "dicts": [
            {"type": "地层", "count": 26}, {"type": "岩性", "count": 48},
            {"type": "图像类型", "count": 10}, {"type": "实验类型", "count": 15},
            {"type": "库存状态", "count": 6},
        ],
        "counts": {
            "wells": one(conn, "SELECT COUNT(*) c FROM wells")["c"],
            "images": one(conn, "SELECT COUNT(*) c FROM images")["c"],
            "sections": one(conn, "SELECT COUNT(*) c FROM sections")["c"],
            "experiments": one(conn, "SELECT COUNT(*) c FROM experiments")["c"],
        },
    }


def post_annotation(conn, iid, body):
    img = one(conn, "SELECT id FROM images WHERE id=?", (iid,))
    if not img:
        return None
    geom = body.get("geometry") or {}
    cur = conn.execute("""INSERT INTO annotations(image_id,type,geometry,value,unit,label,author,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",
        (iid, body.get("type", "length"), json.dumps(geom, ensure_ascii=False),
         body.get("value"), body.get("unit", "mm"), body.get("label", ""),
         body.get("author", "admin"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    return {"id": cur.lastrowid}


def post_txn(conn, body):
    sid = body.get("section_id")
    sec = one(conn, "SELECT * FROM sections WHERE id=?", (sid,))
    if not sec:
        return None
    typ = body.get("txn_type", "入库")
    qty = float(body.get("quantity", sec["length"]))
    reason = body.get("reason", "")
    inv = one(conn, "SELECT * FROM inventory WHERE section_id=?", (sid,))
    if inv:
        status = "在库" if typ in ("入库", "归还") else ("借出" if typ == "借阅" else ("损耗" if typ == "损耗" else inv["status"]))
        conn.execute("UPDATE inventory SET status=?, quantity=?, updated_at=? WHERE id=?",
                     (status, qty, datetime.now().strftime("%Y-%m-%d"), inv["id"]))
        from_loc, to_loc = inv["location"], inv["location"]
    else:
        from_loc, to_loc = "", "1号库-1排-1架-001箱-1格"
        conn.execute("INSERT INTO inventory(well_id,section_id,location,quantity,unit,status,updated_at) VALUES(?,?,?,?,?,?,?)",
                     (sec["well_id"], sid, to_loc, qty, "m", "在库", datetime.now().strftime("%Y-%m-%d")))
    conn.execute("""INSERT INTO txns(well_id,section_id,txn_type,quantity,unit,from_loc,to_loc,operator,txn_time,reason)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (sec["well_id"], sid, typ, qty, "m", from_loc, to_loc, body.get("operator", "admin"),
         datetime.now().strftime("%Y-%m-%d %H:%M"), reason))
    conn.commit()
    return {"ok": True}


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "CoreDemo/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        qs = parse_qs(parsed.query)
        if path.startswith("/api/"):
            conn = db()
            try:
                if path == "/api/health":
                    return ok(self, {"ok": True, "time": datetime.now().isoformat()})
                if path == "/api/overview":
                    return ok(self, api_overview(conn))
                if path == "/api/wells":
                    return ok(self, api_wells(conn, qs))
                m = re.match(r"^/api/wells/(\d+)$", path)
                if m:
                    data = api_well_detail(conn, int(m.group(1)))
                    return ok(self, data) if data else fail(self, "well not found", 404)
                m = re.match(r"^/api/images/(\d+)$", path)
                if m:
                    data = api_image_detail(conn, int(m.group(1)))
                    return ok(self, data) if data else fail(self, "image not found", 404)
                if path == "/api/search":
                    return ok(self, api_search(conn, qs))
                if path == "/api/stats":
                    return ok(self, api_stats(conn))
                if path == "/api/inventory":
                    return ok(self, api_inventory(conn, qs))
                if path == "/api/admin":
                    return ok(self, api_admin(conn))
                return fail(self, "not found", 404)
            except Exception as e:
                sys.stderr.write("API error %s: %s\n" % (path, e))
                return fail(self, str(e), 500)
            finally:
                conn.close()
        self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}") if length else {}
        except Exception as e:
            return fail(self, "invalid json: %s" % e, 400)
        conn = db()
        try:
            m = re.match(r"^/api/images/(\d+)/annotations$", path)
            if m:
                data = post_annotation(conn, int(m.group(1)), body)
                return ok(self, data) if data else fail(self, "image not found", 404)
            if path == "/api/inventory/txn":
                data = post_txn(conn, body)
                return ok(self, data) if data else fail(self, "section not found", 404)
            return fail(self, "not found", 404)
        except Exception as e:
            sys.stderr.write("POST error %s: %s\n" % (path, e))
            return fail(self, str(e), 500)
        finally:
            conn.close()

    def serve_static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        rel = path.lstrip("/").replace("\\", "/")
        target = (STATIC / rel).resolve()
        if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
            # SPA fallback for non-file routes
            if "." not in Path(path).name:
                target = STATIC / "index.html"
            else:
                self.send_error(404, "Not Found")
                return
        ctype, _ = mimetypes.guess_type(str(target))
        ctype = ctype or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if target.suffix.lower() in (".jpg", ".jpeg", ".png", ".svg", ".webp"):
            self.send_header("Cache-Control", "public, max-age=3600")
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="Core database demo server")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    if not DB_PATH.exists():
        print("database not found, run: python app/seed.py")
        sys.exit(1)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Core demo running at http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
