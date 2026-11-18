# -*- coding: utf-8 -*-
"""Chart template registry and per-well chart outputs."""
import json
import time

import audit
from db_backend import is_postgres
from entry import EntryError, _one, _rows

STATUSES = ("未生成", "生成中", "已生成", "失败")


def categories(conn):
    return _rows(conn, "SELECT code, name, sort_no FROM chart_category ORDER BY sort_no, code")


def templates(conn, include_inactive=False):
    where = "" if include_inactive else "WHERE t.is_active"
    items = _rows(conn, f"""SELECT t.*, c.name AS category_name,
        (SELECT COUNT(*) FROM well_chart wc WHERE wc.template_id=t.id AND wc.status='已生成') AS generated_count
        FROM chart_template t JOIN chart_category c ON c.code=t.category_code
        {where} ORDER BY c.sort_no, t.sort_no, t.version""")
    return {"categories": categories(conn), "items": items}


def well_charts(conn, well_id):
    well = _one(conn, "SELECT id, code, name FROM wells WHERE id=? AND deleted_at IS NULL", (well_id,))
    if not well:
        raise EntryError("井不存在", 404)
    items = _rows(conn, """SELECT t.*, c.name AS category_name,
        wc.id AS chart_id, wc.status, wc.file_url, wc.image_url,
        wc.generated_at, wc.generated_by, wc.error_msg
        FROM chart_template t JOIN chart_category c ON c.code=t.category_code
        LEFT JOIN well_chart wc ON wc.template_id=t.id AND wc.well_id=?
        WHERE t.is_active ORDER BY c.sort_no, t.sort_no, t.version""", (well_id,))
    return {"well": well, "categories": categories(conn), "items": items}


def set_status(conn, well_id, template_id, body, actor="system"):
    if not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=? AND deleted_at IS NULL", (well_id,)):
        raise EntryError("井不存在", 404)
    t = _one(conn, "SELECT * FROM chart_template WHERE id=? AND is_active", (template_id,))
    if not t:
        raise EntryError("模板不存在或已停用", 404)
    status = str(body.get("status") or "已生成")
    if status not in STATUSES:
        raise EntryError("成果状态不正确", 400)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    by = actor.get("account") if isinstance(actor, dict) else str(actor or "system")
    file_url = body.get("file_url") or None
    image_url = body.get("image_url") or None
    error = body.get("error_msg") or None
    try:
        conn.execute("""INSERT INTO well_chart(well_id,template_id,status,file_url,image_url,generated_at,generated_by,error_msg)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(well_id,template_id) DO UPDATE SET
              status=excluded.status, file_url=excluded.file_url, image_url=excluded.image_url,
              generated_at=excluded.generated_at, generated_by=excluded.generated_by, error_msg=excluded.error_msg""",
            (well_id, template_id, status, file_url, image_url, now, by, error))
        audit.log(conn, actor, "图件成果", f"{t['name']} / 井 #{well_id}",
                  {"status": status, "template_id": template_id})
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise EntryError(f"成果状态写入失败：{str(e)[:180]}", 500)
    return {"well_id": well_id, "template_id": template_id, "status": status}


def create_template(conn, body, actor="system"):
    code = str(body.get("code") or "").strip().upper()
    name = str(body.get("name") or "").strip()
    category = str(body.get("category_code") or "").strip()
    version = str(body.get("version") or "").strip()
    project = str(body.get("project") or "").strip()
    output = str(body.get("output_type") or "交互图").strip()
    if not code or not name or not category:
        raise EntryError("模板编码、名称、分类不能为空", 400)
    if not _one(conn, "SELECT 1 AS ok FROM chart_category WHERE code=?", (category,)):
        raise EntryError("模板分类不存在", 400)
    if _one(conn, "SELECT 1 AS ok FROM chart_template WHERE code=? AND version=? AND project=?",
            (code, version, project)):
        raise EntryError("同编码、版本、项目的模板已存在", 409)
    config = body.get("config_json") or {}
    if not isinstance(config, str):
        config = json.dumps(config, ensure_ascii=False)
    active = bool(int(body.get("is_active", 1))) if is_postgres() else int(body.get("is_active", 1))
    try:
        if is_postgres():
            cur = conn.execute("""INSERT INTO chart_template
                (code,name,category_code,version,project,output_type,config_json,is_active,sort_no)
                VALUES(?,?,?,?,?,?,?::jsonb,?,?) RETURNING id""",
                (code, name, category, version, project, output, config,
                 active, int(body.get("sort_no", 0))))
            new_id = cur.fetchone()["id"]
        else:
            cur = conn.execute("""INSERT INTO chart_template
                (code,name,category_code,version,project,output_type,config_json,is_active,sort_no)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (code, name, category, version, project, output, config,
                 active, int(body.get("sort_no", 0))))
            new_id = cur.lastrowid
        audit.log(conn, actor, "新增模板", f"{name} #{new_id}", {"code": code})
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise EntryError(f"模板写入失败：{str(e)[:180]}", 500)
    return {"id": new_id, "code": code, "name": name}


def update_template(conn, template_id, body, actor="system"):
    row = _one(conn, "SELECT * FROM chart_template WHERE id=?", (template_id,))
    if not row:
        raise EntryError("模板不存在", 404)
    allowed = {"name": "name", "category_code": "category_code", "version": "version",
               "project": "project", "output_type": "output_type", "is_active": "is_active",
               "sort_no": "sort_no", "config_json": "config_json"}
    data = {}
    for src, col in allowed.items():
        if src in body:
            data[col] = body[src]
    if not data:
        raise EntryError("没有可更新的字段", 400)
    if "category_code" in data and not _one(conn, "SELECT 1 AS ok FROM chart_category WHERE code=?", (data["category_code"],)):
        raise EntryError("模板分类不存在", 400)
    if "config_json" in data and not isinstance(data["config_json"], str):
        data["config_json"] = json.dumps(data["config_json"], ensure_ascii=False)
    if "is_active" in data:
        data["is_active"] = bool(int(data["is_active"])) if is_postgres() else int(data["is_active"])
    sets = ", ".join((f"{c}=?::jsonb" if c == "config_json" and is_postgres() else f"{c}=?") for c in data)
    try:
        conn.execute(f"UPDATE chart_template SET {sets} WHERE id=?", list(data.values()) + [template_id])
        audit.log(conn, actor, "更新模板", f"模板 #{template_id}", data)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise EntryError(f"模板更新失败：{str(e)[:180]}", 500)
    return {"id": template_id, "updated": True}
