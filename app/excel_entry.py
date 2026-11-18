# -*- coding: utf-8 -*-
"""Excel template generation and batch import for the data-entry entities."""
import base64
import io
from datetime import date, datetime, time

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from entry import ENTITIES, EntryError, create


def _as_text(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, str):
        return value.strip()
    return value


def _rows(conn, sql):
    return [dict(r) for r in conn.execute(sql).fetchall()]


def template(conn, entity):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    wb = Workbook()
    ws = wb.active
    ws.title = spec["label"][:31]
    headers = [f["label"] for f in spec["fields"]]
    ws.append(headers)
    ws.freeze_panes = "A2"
    for i, f in enumerate(spec["fields"], 1):
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(28, len(f["label"]) * 2 + 6))
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B3B5A")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    guide = wb.create_sheet("填写说明")
    guide.append(["字段", "名称", "必填", "类型", "填写提示"])
    ref_hint = {
        "well_id": "可填井 ID 或井号（如 BD16）",
        "run_id": "可填回次 ID，或“井号/回次号”（如 BD16/1）",
        "section_id": "可填段 ID，或“井号/回次号/段号”（如 BD16/1/1-01）",
        "sample_id": "可填样品 ID 或样品号",
        "sidewall_id": "可填井壁取心 ID 或样品号",
    }
    for f in spec["fields"]:
        hint = ref_hint.get(f["name"], f.get("placeholder", ""))
        guide.append([f["name"], f["label"], "是" if f.get("required") else "否",
                      f.get("type", "text"), hint])
    for i, w in enumerate([20, 18, 8, 12, 34], 1):
        guide.column_dimensions[get_column_letter(i)].width = w
    for c in guide[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="0B3B5A")

    # reference IDs for parent fields
    tries = [
        ("参考-井", "SELECT id, code, name FROM wells ORDER BY id", ["井ID", "井号", "井名"]),
        ("参考-回次", "SELECT id, well_id, run_no FROM runs ORDER BY well_id, run_no", ["回次ID", "井ID", "回次号"]),
        ("参考-岩心段", "SELECT id, well_id, run_id, section_no FROM sections ORDER BY well_id, run_id, id",
         ["段ID", "井ID", "回次ID", "段号"]),
        ("参考-样品", "SELECT id, well_id, sample_no FROM samples ORDER BY id", ["样品ID", "井ID", "样品号"]),
    ]
    for title, sql, head in tries:
        sh = wb.create_sheet(title)
        sh.append(head)
        for r in _rows(conn, sql):
            sh.append(list(r.values()))
        for c in sh[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="0B3B5A")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def import_rows(conn, entity, filename, data_b64, actor="system", dry_run=False):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    if not str(filename).lower().endswith((".xlsx", ".xlsm")):
        raise EntryError("只支持 .xlsx / .xlsm 文件", 400)
    raw = data_b64.split(",", 1)[-1] if "," in data_b64 else data_b64
    try:
        blob = base64.b64decode(raw, validate=True)
    except Exception:
        raise EntryError("文件内容不是有效的 Base64", 400)
    if len(blob) > 8 * 1024 * 1024:
        raise EntryError("文件超过 8 MB 限制", 400)
    try:
        wb = load_workbook(io.BytesIO(blob), data_only=True, read_only=True)
    except Exception as e:
        raise EntryError(f"无法读取 Excel：{e}", 400)

    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        raise EntryError("Excel 为空", 400)
    aliases = {}
    for idx, value in enumerate(header):
        if value is None:
            continue
        key = str(value).strip()
        for f in spec["fields"]:
            if key in (f["name"], f["label"]):
                aliases[f["name"]] = idx
                break

    missing = [f["label"] for f in spec["fields"] if f.get("required") and f["name"] not in aliases]
    if missing:
        raise EntryError("缺少必填列：" + "、".join(missing), 400)

    total = created = 0
    errors = []
    ids = []
    for row_no, row in enumerate(rows, start=2):
        total += 1
        if total > 500:
            errors.append({"row": row_no, "error": "单次最多导入 500 行，后续行未处理"})
            break
        body = {}
        for name, idx in aliases.items():
            body[name] = _as_text(row[idx]) if idx < len(row) else None
        if all(v is None or str(v).strip() == "" for v in body.values()):
            continue
        try:
            r = create(conn, entity, body, actor=actor, dry_run=dry_run)
            created += 1
            if r.get("id") is not None:
                ids.append(r.get("id"))
        except EntryError as e:
            errors.append({"row": row_no, "error": e.message})
        except Exception as e:
            errors.append({"row": row_no, "error": str(e)[:200]})
    wb.close()
    return {"entity": entity, "label": spec["label"], "total": total,
            "created": created, "failed": len(errors), "ids": ids, "errors": errors[:50],
            "dry_run": bool(dry_run)}
