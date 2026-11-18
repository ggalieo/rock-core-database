# -*- coding: utf-8 -*-
"""Metadata-driven data entry for the core database.

The same definitions drive the web form and server-side validation.
All table/column names come from this module, never from the request.
"""
import re
from datetime import datetime

from db_backend import is_postgres


class EntryError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _f(name, label, typ="text", required=False, **kw):
    d = {"name": name, "label": label, "type": typ, "required": required}
    d.update(kw)
    return d


ENTITIES = {
    "well": {
        "label": "井",
        "icon": "◫",
        "table": "wells",
        "desc": "新增一口井，井号不能重复。",
        "label_expr": "code || ' ' || COALESCE(name,'')",
        "fields": [
            _f("code", "井号", required=True, placeholder="例如 BD17"),
            _f("name", "井名", required=True, placeholder="例如 板东17"),
            _f("region", "区块", placeholder="例如 板桥"),
            _f("tectonic", "构造", placeholder="例如 板桥断阶"),
            _f("year", "年份", "int", placeholder="2026"),
            _f("type", "井别", placeholder="预探井 / 评价井 / 开发井"),
            _f("lon", "经度", "number", placeholder="117.123456"),
            _f("lat", "纬度", "number", placeholder="38.123456"),
            _f("kb", "补心海拔", "number"),
            _f("ground", "地面海拔", "number"),
            _f("final_depth", "完钻井深", "number"),
            _f("status", "扫描状态", "select", options=["未扫描", "部分扫描", "已扫描"]),
            _f("operator", "录入人", placeholder="admin"),
        ],
    },
    "run": {
        "label": "取心回次",
        "icon": "▤",
        "table": "runs",
        "desc": "回次号在同一口井内不能重复；顶底深单位 m。",
        "label_expr": "CAST(run_no AS text) || ' 回次'",
        "fields": [
            _f("well_id", "所属井", "select", True, options={"kind": "wells"}),
            _f("run_no", "回次号", "int", True, placeholder="例如 1"),
            _f("top_md", "顶深", "number"),
            _f("bottom_md", "底深", "number"),
            _f("footage", "进尺", "number"),
            _f("core_length", "心长", "number"),
            _f("recovery", "收获率", "number", placeholder="%"),
            _f("layer", "层位"),
            _f("lithology", "岩性"),
            _f("description", "描述", "textarea", wide=True),
            _f("drilled_at", "取心日期", "date"),
        ],
    },
    "section": {
        "label": "岩心段",
        "icon": "▥",
        "table": "sections",
        "desc": "选择回次后自动带出井；段长留空时按顶底深计算。",
        "label_expr": "section_no",
        "fields": [
            _f("run_id", "所属回次", "select", True, options={"kind": "runs"}),
            _f("section_no", "段号", required=True, placeholder="例如 1-01"),
            _f("top_md", "顶深", "number"),
            _f("bottom_md", "底深", "number"),
            _f("length", "段长", "number"),
            _f("box_no", "岩心箱号"),
            _f("slot", "格位"),
            _f("condition", "岩心状态", placeholder="完整 / 破碎 / 磨损"),
            _f("oil_show", "含油程度"),
            _f("fluorescence", "荧光"),
            _f("rqd", "RQD", "number"),
            _f("lithology", "岩性"),
            _f("color", "颜色"),
            _f("description", "描述", "textarea", wide=True),
        ],
    },
    "observation": {
        "label": "岩心观察",
        "icon": "◇",
        "table": "core_observation",
        "desc": "一个岩心段只能有一条观察记录，覆盖 2017 岩心 13 项。",
        "label_expr": "'段 ' || CAST(section_id AS text)",
        "fields": [
            _f("section_id", "岩心段", "select", True, options={"kind": "sections"}),
            _f("structure_code", "结构", "select", options={"kind": "dict", "type": "structure"}),
            _f("structure_desc", "结构描述", "textarea", wide=True),
            _f("sedimentary_structure_code", "构造", "select", options={"kind": "dict", "type": "sedimentary_structure"}),
            _f("sedimentary_structure_desc", "构造描述", "textarea", wide=True),
            _f("fracture_desc", "裂缝描述", "textarea", wide=True),
            _f("fracture_density", "裂缝密度", "number", placeholder="条/m"),
            _f("fracture_angle", "裂缝角度", "number", placeholder="°"),
            _f("vug_desc", "孔洞描述", "textarea", wide=True),
            _f("vug_size_mm", "孔洞尺寸", "number", placeholder="mm"),
            _f("vug_area_pct", "面孔率", "number", placeholder="%"),
            _f("contact_relation_code", "接触关系", "select", options={"kind": "dict", "type": "contact"}),
            _f("fossil_desc", "化石", "textarea", wide=True),
            _f("dip_angle", "倾角", "number", placeholder="°"),
            _f("gas_show_code", "含气情况", "select", options={"kind": "dict", "type": "gas_show"}),
            _f("breakage_wear_code", "破碎/磨损", "select", options={"kind": "dict", "type": "breakage_wear"}),
            _f("observer", "观察人"),
            _f("observed_at", "观察日期", "date"),
            _f("remark", "备注", "textarea", wide=True),
        ],
    },
    "fracture": {
        "label": "裂缝",
        "icon": "╱",
        "table": "core_fracture",
        "desc": "逐条裂缝；同段可多条，裂缝编号建议唯一。",
        "label_expr": "COALESCE(fracture_no,'裂缝') || ' / 段 ' || CAST(section_id AS text)",
        "fields": [
            _f("section_id", "岩心段", "select", True, options={"kind": "sections"}),
            _f("fracture_no", "裂缝编号", placeholder="例如 F-01"),
            _f("type_code", "裂缝类型", "select", options={"kind": "dict", "type": "fracture_type"}),
            _f("dip_angle", "倾角", "number", placeholder="°"),
            _f("strike_angle", "走向", "number", placeholder="°"),
            _f("length_mm", "长度", "number", placeholder="mm"),
            _f("width_mm", "宽度", "number", placeholder="mm"),
            _f("fill_code", "充填物", "select", options={"kind": "dict", "type": "fill"}),
            _f("density_per_m", "密度", "number", placeholder="条/m"),
            _f("description", "描述", "textarea", wide=True),
        ],
    },
    "vug": {
        "label": "孔洞",
        "icon": "○",
        "table": "core_vug",
        "desc": "逐条孔洞；面积单位 mm²，面孔率单位 %。",
        "label_expr": "COALESCE(vug_no,'孔洞') || ' / 段 ' || CAST(section_id AS text)",
        "fields": [
            _f("section_id", "岩心段", "select", True, options={"kind": "sections"}),
            _f("vug_no", "孔洞编号", placeholder="例如 V-01"),
            _f("type_code", "孔洞类型", "select", options={"kind": "dict", "type": "vug_type"}),
            _f("size_mm", "尺寸", "number", placeholder="mm"),
            _f("area_mm2", "面积", "number", placeholder="mm²"),
            _f("area_pct", "面孔率", "number", placeholder="%"),
            _f("fill_code", "充填物", "select", options={"kind": "dict", "type": "fill"}),
            _f("description", "描述", "textarea", wide=True),
        ],
    },
    "sidewall": {
        "label": "井壁取心",
        "icon": "◉",
        "table": "core_sidewall",
        "desc": "井级对象，不挂回次；样品号不能重复。",
        "label_expr": "sample_no || ' / ' || CAST(depth_md AS text) || 'm'",
        "fields": [
            _f("well_id", "所属井", "select", True, options={"kind": "wells"}),
            _f("sample_no", "样品号", required=True, placeholder="例如 SW-001"),
            _f("depth_md", "深度", "number", placeholder="m"),
            _f("lithology", "岩性"),
            _f("oil_show", "含油程度"),
            _f("fluorescence", "荧光"),
            _f("description", "描述", "textarea", wide=True),
            _f("analysis_summary", "分析摘要", "textarea", wide=True),
            _f("collected_at", "采集日期", "date"),
        ],
    },
    "sample": {
        "label": "样品",
        "icon": "▣",
        "table": "samples",
        "desc": "样品必须属于一个岩心段或一颗井壁取心，二选一。",
        "label_expr": "sample_no",
        "fields": [
            _f("sample_no", "样品号", required=True, placeholder="例如 S-001"),
            _f("well_id", "所属井", "select", options={"kind": "wells"}),
            _f("section_id", "岩心段", "select", options={"kind": "sections"}),
            _f("sidewall_id", "井壁取心", "select", options={"kind": "sidewalls"}),
            _f("sample_type", "样品类型", "select", options={"kind": "dict", "type": "sample_type"}),
            _f("top_md", "顶深", "number"),
            _f("bottom_md", "底深", "number"),
            _f("keeper", "保管人"),
            _f("status", "状态", "select", options=["待实验", "实验中", "已完成"]),
            _f("collected_at", "采集日期", "date"),
        ],
    },
    "experiment": {
        "label": "实验",
        "icon": "⌁",
        "table": "experiments",
        "desc": "选择样品后自动带出井、样品号、顶底深。",
        "label_expr": "test_type || ' / ' || COALESCE(param,'')",
        "fields": [
            _f("sample_id", "样品", "select", True, options={"kind": "samples"}),
            _f("test_type", "实验类型", required=True, placeholder="例如 孔隙度"),
            _f("analysis_group", "分析大类", "select", options={"kind": "dict", "type": "analysis_group"}),
            _f("param", "参数"),
            _f("value", "数值", "number"),
            _f("unit", "单位", placeholder="例如 % / 10⁻³μm²"),
            _f("lab", "实验室"),
            _f("method", "方法"),
            _f("detection_limit", "检出限"),
            _f("quality", "质量", placeholder="合格 / 可疑"),
            _f("test_date", "实验日期", "date"),
        ],
    },
    "coring_plan": {
        "label": "取心设计",
        "icon": "◎",
        "table": "coring_plan",
        "desc": "每个回次只能有一条取心设计。",
        "label_expr": "'回次 ' || CAST(run_id AS text)",
        "fields": [
            _f("run_id", "取心回次", "select", True, options={"kind": "runs"}),
            _f("purpose", "取心目的", "textarea", wide=True),
            _f("principle", "取心原则", "textarea", wide=True),
            _f("design_top_md", "设计顶深", "number"),
            _f("design_bottom_md", "设计底深", "number"),
            _f("design_footage", "设计进尺", "number"),
            _f("design_core_length", "设计心长", "number"),
            _f("change_reason", "变更原因", "textarea", wide=True),
            _f("approved_by", "审批人"),
            _f("approved_at", "审批日期", "date"),
        ],
    },
}


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _one(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def _options(conn):
    wells = _rows(conn, "SELECT id, code, name, code || ' ' || name AS label FROM wells ORDER BY code")
    runs = _rows(conn, """SELECT r.id, r.well_id, r.run_no,
        w.code || ' / 第' || CAST(r.run_no AS text) || ' 筒' AS label
        FROM runs r JOIN wells w ON w.id=r.well_id ORDER BY w.code, r.run_no""")
    sections = _rows(conn, """SELECT s.id, s.well_id, s.run_id,
        w.code || ' / 第' || CAST(r.run_no AS text) || ' 筒 / ' || s.section_no AS label
        FROM sections s JOIN runs r ON r.id=s.run_id JOIN wells w ON w.id=s.well_id
        ORDER BY w.code, r.run_no, s.section_no""")
    sidewalls = _rows(conn, """SELECT cs.id, cs.well_id,
        cs.sample_no || ' / ' || w.code || ' / ' || COALESCE(CAST(cs.depth_md AS text),'') || 'm' AS label
        FROM core_sidewall cs JOIN wells w ON w.id=cs.well_id ORDER BY cs.id DESC""")
    samples = _rows(conn, """SELECT s.id, s.well_id, s.sample_no,
        s.sample_no || ' / ' || w.code || ' / ' || COALESCE(s.sample_type,'') AS label
        FROM samples s JOIN wells w ON w.id=s.well_id ORDER BY s.id DESC""")
    dicts = {}
    for r in _rows(conn, "SELECT dict_type, code, name FROM dictionary ORDER BY dict_type, sort_no, code"):
        dicts.setdefault(r["dict_type"], []).append({"value": r["code"], "label": r["name"]})
    return {"wells": wells, "runs": runs, "sections": sections,
            "sidewalls": sidewalls, "samples": samples, "dicts": dicts}


def meta(conn):
    return {"entities": [
        {"key": k, "label": v["label"], "icon": v.get("icon", ""), "desc": v.get("desc", ""),
         "fields": v["fields"]}
        for k, v in ENTITIES.items()
    ], "options": _options(conn)}


def recent(conn, entity):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    sql = f'SELECT id, {spec["label_expr"]} AS label FROM {spec["table"]} ORDER BY id DESC LIMIT 8'
    return {"entity": entity, "label": spec["label"], "items": _rows(conn, sql)}


def _clean(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _convert(field, value):
    name, label, typ = field["name"], field["label"], field.get("type", "text")
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
    if value == "":
        return None
    try:
        if typ == "int":
            return int(float(value))
        if typ == "number":
            v = float(value)
            if v != v or v in (float("inf"), float("-inf")):
                raise ValueError
            return v
        if typ in ("date", "datetime"):
            raw = str(value).replace("T", " ")
            datetime.strptime(raw, "%Y-%m-%d" if typ == "date" else "%Y-%m-%d %H:%M")
            return raw
        return str(value)
    except Exception:
        raise EntryError(f"{label}格式不正确", 400)


def _check_choice(conn, field, value):
    opt = field.get("options")
    if not opt or value is None:
        return
    if isinstance(opt, dict) and opt.get("kind") == "dict":
        if not _one(conn, "SELECT 1 AS ok FROM dictionary WHERE dict_type=? AND code=?", (opt["type"], value)):
            raise EntryError(f"{field['label']}不在字典中", 400)
    elif isinstance(opt, list) and value not in opt:
        raise EntryError(f"{field['label']}取值不正确", 400)


def create(conn, entity, body):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)

    data = {}
    for field in spec["fields"]:
        val = _convert(field, body.get(field["name"]))
        if field.get("required") and val is None:
            raise EntryError(f"请填写{field['label']}", 400)
        if val is not None:
            _check_choice(conn, field, val)
            data[field["name"]] = val

    # parent checks and automatic fields
    if entity == "well":
        if _one(conn, "SELECT 1 AS ok FROM wells WHERE code=?", (data["code"],)):
            raise EntryError("井号已存在", 409)
    elif entity == "run":
        if not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (data["well_id"],)):
            raise EntryError("所属井不存在", 400)
        if data.get("top_md") is not None and data.get("bottom_md") is not None and data["bottom_md"] <= data["top_md"]:
            raise EntryError("底深必须大于顶深", 400)
        if _one(conn, "SELECT 1 AS ok FROM runs WHERE well_id=? AND run_no=?", (data["well_id"], data["run_no"])):
            raise EntryError("该井回次号已存在", 409)
    elif entity == "section":
        run = _one(conn, "SELECT * FROM runs WHERE id=?", (data["run_id"],))
        if not run:
            raise EntryError("所属回次不存在", 400)
        data["well_id"] = run["well_id"]
        if data.get("top_md") is not None and data.get("bottom_md") is not None:
            if data["bottom_md"] <= data["top_md"]:
                raise EntryError("底深必须大于顶深", 400)
            if data.get("length") is None:
                data["length"] = round(data["bottom_md"] - data["top_md"], 3)
        if _one(conn, "SELECT 1 AS ok FROM sections WHERE run_id=? AND section_no=?", (data["run_id"], data["section_no"])):
            raise EntryError("该回次段号已存在", 409)
    elif entity == "observation":
        if not _one(conn, "SELECT 1 AS ok FROM sections WHERE id=?", (data["section_id"],)):
            raise EntryError("岩心段不存在", 400)
        if _one(conn, "SELECT 1 AS ok FROM core_observation WHERE section_id=?", (data["section_id"],)):
            raise EntryError("该岩心段已有观察记录", 409)
    elif entity in ("fracture", "vug"):
        if not _one(conn, "SELECT 1 AS ok FROM sections WHERE id=?", (data["section_id"],)):
            raise EntryError("岩心段不存在", 400)
    elif entity == "sidewall":
        if not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (data["well_id"],)):
            raise EntryError("所属井不存在", 400)
        if _one(conn, "SELECT 1 AS ok FROM core_sidewall WHERE sample_no=?", (data["sample_no"],)):
            raise EntryError("井壁取心样品号已存在", 409)
    elif entity == "sample":
        if data.get("section_id") and data.get("sidewall_id"):
            raise EntryError("样品只能属于岩心段或井壁取心之一", 400)
        if not data.get("section_id") and not data.get("sidewall_id"):
            raise EntryError("请选择岩心段或井壁取心", 400)
        if data.get("section_id"):
            sec = _one(conn, "SELECT * FROM sections WHERE id=?", (data["section_id"],))
            if not sec:
                raise EntryError("岩心段不存在", 400)
            data["well_id"] = sec["well_id"]
            if data.get("top_md") is None: data["top_md"] = sec["top_md"]
            if data.get("bottom_md") is None: data["bottom_md"] = sec["bottom_md"]
        else:
            sw = _one(conn, "SELECT * FROM core_sidewall WHERE id=?", (data["sidewall_id"],))
            if not sw:
                raise EntryError("井壁取心不存在", 400)
            data["well_id"] = sw["well_id"]
            if data.get("top_md") is None: data["top_md"] = sw["depth_md"]
            if data.get("bottom_md") is None: data["bottom_md"] = sw["depth_md"]
        if _one(conn, "SELECT 1 AS ok FROM samples WHERE sample_no=?", (data["sample_no"],)):
            raise EntryError("样品号已存在", 409)
    elif entity == "experiment":
        sample = _one(conn, "SELECT * FROM samples WHERE id=?", (data["sample_id"],))
        if not sample:
            raise EntryError("样品不存在", 400)
        data["well_id"] = sample["well_id"]
        data["sample_code"] = sample["sample_no"]
        data["sample_type"] = sample.get("sample_type")
        data["top_md"] = sample.get("top_md")
        data["bottom_md"] = sample.get("bottom_md")
    elif entity == "coring_plan":
        if not _one(conn, "SELECT 1 AS ok FROM runs WHERE id=?", (data["run_id"],)):
            raise EntryError("取心回次不存在", 400)
        if _one(conn, "SELECT 1 AS ok FROM coring_plan WHERE run_id=?", (data["run_id"],)):
            raise EntryError("该回次已有取心设计", 409)

    cols = list(data.keys())
    if not cols:
        raise EntryError("没有可写入的字段", 400)
    ph = ",".join(["?"] * len(cols))
    sql = f'INSERT INTO {spec["table"]} ({", ".join(cols)}) VALUES ({ph})'
    vals = [data[c] for c in cols]
    try:
        if is_postgres():
            cur = conn.execute(sql + " RETURNING id", vals)
            row = cur.fetchone()
            new_id = row["id"] if row else None
        else:
            cur = conn.execute(sql, vals)
            new_id = cur.lastrowid
        if is_postgres() and new_id:
            if entity == "well" and data.get("lon") is not None and data.get("lat") is not None:
                conn.execute("""INSERT INTO well_geometry(well_id, geom)
                    VALUES (?, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography)""",
                    (new_id, data["lon"], data["lat"]))
            elif entity == "run" and data.get("top_md") is not None and data.get("bottom_md") is not None:
                conn.execute("INSERT INTO run_depth(run_id, depth) VALUES (?, numrange(?, ?, '[)'))",
                             (new_id, data["top_md"], data["bottom_md"]))
            elif entity == "section" and data.get("top_md") is not None and data.get("bottom_md") is not None:
                conn.execute("INSERT INTO section_depth(section_id, depth) VALUES (?, numrange(?, ?, '[)'))",
                             (new_id, data["top_md"], data["bottom_md"]))
            elif entity == "experiment" and data.get("top_md") is not None and data.get("bottom_md") is not None:
                conn.execute("INSERT INTO experiment_depth(experiment_id, depth) VALUES (?, numrange(?, ?, '[)'))",
                             (new_id, data["top_md"], data["bottom_md"]))
        conn.commit()
    except Exception as e:
        conn.rollback() if hasattr(conn, "rollback") else None
        msg = str(e)
        if "UNIQUE" in msg.upper() or "unique" in msg:
            raise EntryError("数据重复，违反唯一约束", 409)
        if "FOREIGN KEY" in msg.upper():
            raise EntryError("关联数据不存在", 400)
        raise EntryError(f"写入失败：{msg[:200]}", 500)
    return {"id": new_id, "entity": entity, "label": spec["label"]}
