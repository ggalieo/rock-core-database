# -*- coding: utf-8 -*-
"""Generate a real composite core column (PNG) from structured core data."""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import audit

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
OUT_DIR = STATIC / "generated" / "reports"
FONT = "C:/Windows/Fonts/msyh.ttc"
FONT_B = "C:/Windows/Fonts/msyhbd.ttc"

W, H = 1680, 2200
LEFT, TOP, RIGHT, BOTTOM = 46, 190, 34, 70


class RenderError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def _rows(conn, sql, params=()):
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def _hash_rows(rows):
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def _wrap(d, text, f, max_w, max_lines=6):
    text = (text or "").replace("\r", "").strip()
    if not text:
        return []
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if d.textlength(cur + ch, font=f) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
        if len(lines) >= max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len("".join(lines)) < len(text):
        lines[-1] = lines[-1][:max(0, len(lines[-1]) - 1)] + "…"
    return lines


def _section_at(sections, depth):
    for s in sections:
        if s["top_md"] is not None and s["bottom_md"] is not None:
            if s["top_md"] <= depth < s["bottom_md"]:
                return s
    return None


def _analysis(conn, well_id):
    return _rows(conn, """SELECT r.*, b.batch_no, b.lab, b.method, s.sample_no, s.top_md, s.bottom_md
        FROM analysis_result r JOIN analysis_batch b ON b.id=r.batch_id
        LEFT JOIN samples s ON s.id=r.sample_id
        WHERE b.well_id=? AND r.deleted_at IS NULL AND b.deleted_at IS NULL
        ORDER BY s.top_md, r.id""", (well_id,))


def _render(conn, well, template, runs, sections, descriptions, samples, images, results):
    dmin = min([r["top_md"] for r in runs if r["top_md"] is not None] or [0])
    dmax = max([r["bottom_md"] for r in runs if r["bottom_md"] is not None] or [dmin + 1])
    if dmax <= dmin:
        dmax = dmin + 1
    plot_bottom = H - BOTTOM
    plot_h = plot_bottom - TOP

    def yy(depth):
        return TOP + (depth - dmin) / (dmax - dmin) * plot_h

    def hh(a, b):
        return max(2, (b - a) / (dmax - dmin) * plot_h)

    im = Image.new("RGB", (W, H), (250, 252, 254))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 9], fill=(11, 59, 90))
    d.rectangle([0, 9, W, 12], fill=(14, 116, 144))

    # header
    d.text((LEFT, 40), "岩心综合柱状图", font=_font(34, True), fill=(11, 59, 90))
    d.text((LEFT, 88), f"{well['code']}  {well['name']}", font=_font(20, True), fill=(30, 50, 70))
    d.text((LEFT, 120), f"{well.get('region','')} · {well.get('tectonic','')} · {well.get('type','')}",
           font=_font(12), fill=(90, 110, 128))
    d.text((W - 410, 44), template["name"], font=_font(18, True), fill=(14, 116, 144))
    d.text((W - 410, 74), f"模板 {template['version']} · {template.get('project') or '通用'}",
           font=_font(12), fill=(100, 118, 134))
    d.text((W - 410, 100), f"深度 {dmin:.2f}—{dmax:.2f} m", font=_font(12), fill=(100, 118, 134))
    d.text((W - 410, 122), datetime.now().strftime("生成 %Y-%m-%d %H:%M"), font=_font(11), fill=(120, 135, 150))
    d.line([LEFT, 162, W - RIGHT, 162], fill=(200, 215, 226), width=1)

    # track geometry
    x = LEFT
    tracks = [
        ("depth", "深度", 76),
        ("strata", "地层", 90),
        ("lith", "岩性", 170),
        ("desc", "岩心描述", 410),
        ("photo", "岩心照片", 250),
        ("por", "孔隙度", 150),
        ("perm", "渗透率", 160),
        ("sample", "样品/实验", 110),
        ("struct", "裂缝/RQD", 100),
    ]
    xs = {}
    for key, label, w in tracks:
        xs[key] = (x, w)
        d.rectangle([x, TOP - 34, x + w - 1, TOP - 1], fill=(234, 243, 249), outline=(204, 220, 231))
        d.text((x + 7, TOP - 26), label, font=_font(12, True), fill=(30, 62, 82))
        x += w
    track_right = x
    d.rectangle([LEFT, TOP, track_right, plot_bottom], outline=(190, 206, 218))

    # horizontal depth grid + labels
    step = 10 if (dmax - dmin) > 80 else 5
    start = int(dmin // step * step)
    dep = start
    while dep <= dmax + step:
        if dep >= dmin - 0.001:
            y = yy(dep)
            d.line([(LEFT, y), (track_right, y)], fill=(226, 235, 242), width=1)
            d.text((xs["depth"][0] + 7, y - 7), f"{dep:.0f}", font=_font(10), fill=(80, 104, 122))
        dep += step

    # strata + sections
    for s in sections:
        if s["top_md"] is None or s["bottom_md"] is None:
            continue
        y0, y1 = yy(s["top_md"]), yy(s["bottom_md"])
        layer = s.get("run_layer") or s.get("layer") or ""
        if layer:
            d.rectangle([xs["strata"][0] + 2, y0, xs["strata"][0] + xs["strata"][1] - 3, y1],
                        fill=(235, 246, 242), outline=(180, 208, 196))
            d.text((xs["strata"][0] + 6, y0 + 3), str(layer)[:8], font=_font(9), fill=(35, 92, 72))
        col = s.get("color") or "#c9b48a"
        try:
            rgb = tuple(int(col.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        except Exception:
            rgb = (190, 175, 145)
        d.rectangle([xs["lith"][0] + 2, y0, xs["lith"][0] + xs["lith"][1] - 3, y1],
                    fill=rgb, outline=(150, 150, 140))
        d.text((xs["lith"][0] + 7, y0 + 3), (s.get("lithology") or "")[:10], font=_font(9), fill=(25, 35, 35))

    # descriptions
    for xdesc in descriptions:
        sec = _section_at(sections, xdesc["interval_top_md"])
        if not sec:
            continue
        y0 = yy(xdesc["interval_top_md"])
        y1 = yy(xdesc["interval_bottom_md"])
        text = "；".join([v for v in [xdesc.get("structure_desc"), xdesc.get("sedimentary_structure_desc"),
                                     xdesc.get("fracture_desc"), xdesc.get("vug_desc"),
                                     xdesc.get("fossil_desc")] if v])
        if not text:
            text = xdesc.get("remark") or ""
        f = _font(9)
        lines = _wrap(d, text, f, xs["desc"][1] - 16, max_lines=max(2, min(8, int((y1 - y0) / 12))))
        for i, line in enumerate(lines):
            d.text((xs["desc"][0] + 7, y0 + 4 + i * 12), line, font=f, fill=(48, 62, 74))

    # photos (section surface images)
    for s in sections:
        if s["top_md"] is None or s["bottom_md"] is None:
            continue
        y0, y1 = yy(s["top_md"]), yy(s["bottom_md"])
        if y1 - y0 < 6:
            continue
        img_row = next((im0 for im0 in images if im0.get("section_id") == s["id"]
                        and im0.get("type") == "SURFACE"), None)
        if not img_row:
            continue
        path = STATIC / (img_row.get("file") or "")
        if not path.is_file():
            continue
        try:
            pic = Image.open(path).convert("RGB")
            target_h = max(2, int(y1 - y0) - 3)
            target_w = xs["photo"][1] - 8
            pic = pic.resize((target_w, target_h), Image.Resampling.LANCZOS)
            im.paste(pic, (xs["photo"][0] + 4, int(y0) + 2))
        except Exception:
            pass

    # analysis curves
    por_vals = [r for r in results if (r.get("test_type") or "").find("孔隙") >= 0 or
                (r.get("param") or "").upper() in ("PHI", "POR", "POROSITY")]
    perm_vals = [r for r in results if (r.get("test_type") or "").find("渗透") >= 0 or
                 (r.get("param") or "").upper() in ("PERM", "K", "PERMEABILITY")]

    def curve(vals, key, vmin, vmax, log=False, color=(14, 116, 144)):
        if not vals:
            d.text((xs[key][0] + 10, TOP + 10), "无数据", font=_font(9), fill=(160, 170, 180))
            return
        pts = []
        for r in vals:
            if r.get("top_md") is None or r.get("value") is None:
                continue
            v = float(r["value"])
            if log:
                if v <= 0:
                    continue
                import math
                p = (math.log10(max(v, vmin)) - math.log10(vmin)) / (math.log10(vmax) - math.log10(vmin))
            else:
                p = (v - vmin) / (vmax - vmin)
            p = max(0, min(1, p))
            pts.append((xs[key][0] + 8 + p * (xs[key][1] - 16), yy(float(r["top_md"]))))
        if len(pts) > 1:
            d.line(pts, fill=color, width=2)
        for px, py in pts:
            d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=color)
        d.text((xs[key][0] + 6, plot_bottom - 16), f"{vmin:g}–{vmax:g}", font=_font(8), fill=(130, 145, 158))

    curve(por_vals, "por", 0, 30, color=(14, 116, 144))
    curve(perm_vals, "perm", 0.01, 1000, log=True, color=(15, 159, 110))

    # samples + analysis markers
    for s in samples:
        if s.get("top_md") is None:
            continue
        y = yy(float(s["top_md"]))
        d.polygon([(xs["sample"][0] + 5, y), (xs["sample"][0] + 15, y - 4),
                   (xs["sample"][0] + 15, y + 4)], fill=(183, 121, 31))
        d.text((xs["sample"][0] + 19, y - 5), (s.get("sample_no") or "")[:10], font=_font(8), fill=(120, 80, 22))

    # fracture/RQD annotations
    for s in sections:
        if s.get("top_md") is None or s.get("bottom_md") is None:
            continue
        y0, y1 = yy(s["top_md"]), yy(s["bottom_md"])
        rqd = s.get("rqd")
        if rqd is not None:
            d.rectangle([xs["struct"][0] + 4, y0 + 3, xs["struct"][0] + 34, y1 - 3], outline=(180, 190, 200))
            d.rectangle([xs["struct"][0] + 4, y1 - 3 - (y1 - y0 - 6) * float(rqd) / 100,
                         xs["struct"][0] + 34, y1 - 3], fill=(117, 168, 142))
            d.text((xs["struct"][0] + 38, y0 + 3), f"RQD {float(rqd):.0f}%", font=_font(8), fill=(70, 94, 84))

    # footer
    d.line([LEFT, H - 44, W - RIGHT, H - 44], fill=(200, 215, 226), width=1)
    d.text((LEFT, H - 34), "由岩心数据库自动生成 · 数据变更后应重新生成", font=_font(9), fill=(120, 135, 150))
    d.text((W - 300, H - 34), f"{well['code']} / {template['code']} / {template['version']}",
           font=_font(9), fill=(120, 135, 150))
    return im


def generate(conn, well_id, template_id, actor="system"):
    if isinstance(actor, dict):
        actor_name = actor.get("account") or actor.get("name") or "system"
    else:
        actor_name = str(actor or "system")
    well = _one(conn, "SELECT * FROM wells WHERE id=? AND deleted_at IS NULL", (well_id,))
    if not well:
        raise RenderError("井不存在", 404)
    template = _one(conn, "SELECT * FROM report_template WHERE id=? AND is_active", (template_id,))
    if not template:
        raise RenderError("成果模板不存在或已停用", 404)
    if template["code"] not in ("CORE_BASIC", "CORE_COMPOSITE"):
        raise RenderError("该成果类型暂未配置生成器", 400)
    runs = _rows(conn, "SELECT * FROM runs WHERE well_id=? AND deleted_at IS NULL ORDER BY run_no", (well_id,))
    if not runs:
        raise RenderError("该井暂无取心回次，无法生成", 400)
    sections = _rows(conn, """SELECT s.*, r.run_no, r.layer AS run_layer FROM sections s
        JOIN runs r ON r.id=s.run_id WHERE s.well_id=? AND s.deleted_at IS NULL ORDER BY s.top_md""", (well_id,))
    descriptions = _rows(conn, """SELECT d.* FROM core_description d JOIN sections s ON s.id=d.section_id
        WHERE s.well_id=? AND d.deleted_at IS NULL AND d.is_current=1 ORDER BY d.interval_top_md""", (well_id,))
    samples = _rows(conn, "SELECT * FROM samples WHERE well_id=? AND deleted_at IS NULL ORDER BY top_md", (well_id,))
    images = _rows(conn, """SELECT * FROM images WHERE well_id=? AND deleted_at IS NULL
        ORDER BY top_md, id""", (well_id,))
    results = _analysis(conn, well_id)

    data_rows = {"well": well, "template": template, "runs": runs, "sections": sections,
                 "descriptions": descriptions, "samples": samples, "images": images,
                 "results": results}
    data_version = _hash_rows(data_rows)
    im = _render(conn, well, template, runs, sections, descriptions, samples, images, results)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    renderer = "CORE_COMPOSITE_PNG" if template["code"] == "CORE_COMPOSITE" else "CORE_BASIC_PNG"
    name = f"well_{well_id}_{template['id']}_{data_version}.png"
    path = OUT_DIR / name
    im.save(path, quality=92)
    raw = path.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    rel = f"/generated/reports/{name}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = _one(conn, "SELECT id FROM report_output WHERE well_id=? AND template_id=?", (well_id, template_id))
    if row:
        conn.execute("""UPDATE report_output SET status='已生成',file_url=?,file_hash=?,file_size=?,
            generated_at=?,generated_by=?,error_msg=NULL,source_type='generated',renderer_key=?,
            template_version=?,data_version=?,review_status='未审核'
            WHERE id=?""",
            (rel, file_hash, len(raw), now, actor_name, renderer, template["version"], data_version, row["id"]))
    else:
        conn.execute("""INSERT INTO report_output
            (well_id,template_id,status,file_url,file_hash,file_size,generated_at,generated_by,
             source_type,renderer_key,template_version,data_version,review_status)
            VALUES(?,?,'已生成',?,?,?,?,?,'generated',?,?,?,'未审核')""",
            (well_id, template_id, rel, file_hash, len(raw), now, actor_name, renderer, template["version"], data_version))
    audit.log(conn, actor, "生成成果", f"{well['code']} / {template['name']}", {"file": rel, "data_version": data_version})
    conn.commit()
    return {"well_id": well_id, "template_id": template_id, "status": "已生成", "file_url": rel,
            "file_hash": file_hash, "file_size": len(raw), "data_version": data_version,
            "template_version": template["version"], "renderer_key": renderer, "generated_at": now}
