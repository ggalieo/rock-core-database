# -*- coding: utf-8 -*-
"""Upload a core image: save local JPG/thumbnail, optionally mirror to S3/MinIO."""
import base64
import hashlib
import io
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

import audit
from db_backend import is_postgres
from entry import EntryError, _one, _resolve_ref
from s3store import client as s3_client, s3_enabled

BASE = Path(__file__).resolve().parent
CORE = BASE / "static" / "assets" / "core"


def _decode(data):
    raw = str(data or "")
    if "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        blob = base64.b64decode(raw, validate=True)
    except Exception:
        raise EntryError("影像数据不是有效的 Base64", 400)
    if len(blob) > 12 * 1024 * 1024:
        raise EntryError("影像超过 12 MB 限制", 400)
    return blob


def create_image(conn, body, actor="system"):
    well_raw = body.get("well_id")
    section_id = body.get("section_id")
    run_id = body.get("run_id")
    if section_id:
        section_id = _resolve_ref(conn, "section_id", section_id)
        sec = _one(conn, "SELECT * FROM sections WHERE id=?", (section_id,))
        if not sec:
            raise EntryError("岩心段不存在", 400)
        well_id = sec["well_id"]
        run_id = sec["run_id"]
        top = body.get("top_md") or sec.get("top_md")
        bottom = body.get("bottom_md") or sec.get("bottom_md")
    elif run_id:
        run_id = _resolve_ref(conn, "run_id", run_id)
        run = _one(conn, "SELECT * FROM runs WHERE id=?", (run_id,))
        if not run:
            raise EntryError("回次不存在", 400)
        well_id = run["well_id"]
        top = body.get("top_md") or run.get("top_md")
        bottom = body.get("bottom_md") or run.get("bottom_md")
    else:
        well_id = _resolve_ref(conn, "well_id", well_raw)
        top = body.get("top_md")
        bottom = body.get("bottom_md")
    if not well_id or not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (well_id,)):
        raise EntryError("请选择有效井", 400)
    if not section_id and not run_id and well_raw is None:
        raise EntryError("请选择井", 400)

    typ = str(body.get("type") or "SURFACE").upper()
    if typ not in ("SURFACE", "ROLLED", "FLUORESCENCE", "BOX", "THIN_SECTION"):
        raise EntryError("影像类型不正确", 400)
    blob = _decode(body.get("file_data"))
    try:
        img = Image.open(io.BytesIO(blob))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception:
        raise EntryError("无法识别影像格式", 400)
    if img.width < 40 or img.height < 40:
        raise EntryError("影像尺寸过小", 400)
    if max(img.width, img.height) > 3200:
        img.thumbnail((3200, 3200), Image.Resampling.LANCZOS)

    name = "upload_" + uuid.uuid4().hex + ".jpg"
    thumb_name = "thumb_" + name
    CORE.mkdir(parents=True, exist_ok=True)
    img.save(CORE / name, quality=90, optimize=True)
    thumb = img.copy()
    thumb.thumbnail((320, 240), Image.Resampling.LANCZOS)
    thumb.save(CORE / thumb_name, quality=84, optimize=True)
    object_key = thumb_key = None
    etag = hashlib.md5(blob).hexdigest()
    if s3_enabled():
        try:
            c = s3_client()
            bucket = __import__("os").environ["S3_BUCKET"]
            c.put_object(Bucket=bucket, Key="core/" + name, Body=(CORE / name).read_bytes(),
                         ContentType="image/jpeg")
            c.put_object(Bucket=bucket, Key="core/" + thumb_name, Body=(CORE / thumb_name).read_bytes(),
                         ContentType="image/jpeg")
            object_key, thumb_key = "core/" + name, "core/" + thumb_name
        except Exception as e:
            raise EntryError(f"MinIO 上传失败：{str(e)[:160]}", 500)

    file_rel = "assets/core/" + name
    thumb_rel = "assets/core/" + thumb_name
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values = {
        "well_id": well_id, "run_id": run_id, "section_id": section_id, "type": typ,
        "light": body.get("light") or ("紫外光" if typ == "FLUORESCENCE" else "自然光"),
        "top_md": top, "bottom_md": bottom, "file": file_rel, "thumb": thumb_rel,
        "width": img.width, "height": img.height, "dpi": 72, "mm_per_px": None,
        "captured_at": body.get("captured_at") or now, "device": body.get("device") or "web-upload",
        "operator": actor.get("account") if isinstance(actor, dict) else str(actor or "system"),
        "quality": body.get("quality") or "合格",
        "object_key": object_key, "thumb_key": thumb_key,
        "content_type": "image/jpeg", "size_bytes": (CORE / name).stat().st_size, "etag": etag,
    }
    cols = list(values)
    try:
        if is_postgres():
            cur = conn.execute(f'INSERT INTO images ({", ".join(cols)}) VALUES ({",".join(["?"]*len(cols))}) RETURNING id',
                               [values[c] for c in cols])
            new_id = cur.fetchone()["id"]
        else:
            cur = conn.execute(f'INSERT INTO images ({", ".join(cols)}) VALUES ({",".join(["?"]*len(cols))})',
                               [values[c] for c in cols])
            new_id = cur.lastrowid
        audit.log(conn, actor, "上传影像", f"影像 #{new_id}", {"well_id": well_id, "type": typ})
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise EntryError(f"影像入库失败：{str(e)[:180]}", 500)
    return {"id": new_id, "entity": "image", "label": "影像", "file": file_rel, "thumb": thumb_rel}


def delete_image(conn, image_id, actor="system"):
    row = _one(conn, "SELECT * FROM images WHERE id=?", (image_id,))
    if not row:
        raise EntryError("影像不存在", 404)
    for table in ("annotations", "image_calibration"):
        n = _one(conn, f"SELECT COUNT(*) AS c FROM {table} WHERE image_id=?", (image_id,))["c"]
        if n:
            raise EntryError(f"存在 {n} 条关联记录，不能删除", 409)
    conn.execute("UPDATE images SET deleted_at=? WHERE id=?",
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), image_id))
    audit.log(conn, actor, "删除影像", f"影像 #{image_id}", {})
    conn.commit()
    return {"id": image_id, "deleted": True}
