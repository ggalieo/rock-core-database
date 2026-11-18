# -*- coding: utf-8 -*-
"""Metadata-driven data entry for the core database.

The same definitions drive the web form and server-side validation.
All table/column names come from this module, never from the request.
"""
import re
from datetime import datetime

from db_backend import is_postgres
import audit


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
        "list_fields": ['code', 'name', 'region', 'year', 'status'],
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
            _f("status", "扫描状态", "select", options=["待扫描", "部分扫描", "已扫描"]),
            _f("operator", "录入人", placeholder="admin"),
        ],
    },
    "run": {
        "label": "取心回次",
        "icon": "▤",
        "table": "runs",
        "list_fields": ['well_id', 'run_no', 'top_md', 'bottom_md', 'recovery'],
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
        "list_fields": ['run_id', 'section_no', 'top_md', 'bottom_md', 'lithology'],
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
    "fracture": {
        "label": "裂缝",
        "icon": "╱",
        "table": "core_fracture",
        "list_fields": ['section_id', 'fracture_no', 'type_code', 'dip_angle'],
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
        "list_fields": ['section_id', 'vug_no', 'type_code', 'area_mm2'],
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
        "list_fields": ['well_id', 'sample_no', 'depth_md', 'lithology'],
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
        "list_fields": ['well_id', 'sample_no', 'section_id', 'sample_type', 'status'],
        "desc": "样品必须属于一个岩心段或一颗井壁取心，二选一。",
        "label_expr": "sample_no",
        "fields": [
            _f("sample_no", "样品号", required=True, placeholder="例如 S-001"),
            _f("well_id", "所属井", "select", options={"kind": "wells"}),
            _f("section_id", "岩心段", "select", options={"kind": "sections"}),
            _f("sidewall_id", "井壁取心", "select", options={"kind": "sidewalls"}),
            _f("parent_sample_id", "母样", "select", options={"kind": "samples"}),
            _f("derived_reason", "派生原因", placeholder="例如 柱塞样 / 薄片"),
            _f("sample_type", "样品类型", "select", options={"kind": "dict", "type": "sample_type"}),
            _f("top_md", "顶深", "number"),
            _f("bottom_md", "底深", "number"),
            _f("keeper", "保管人"),
            _f("status", "状态", "select", options=["已入库", "待实验", "实验中", "已完成"]),
            _f("collected_at", "采集日期", "date"),
        ],
    },
    "coring_plan": {
        "label": "取心设计",
        "icon": "◎",
        "table": "coring_plan",
        "list_fields": ['run_id', 'design_top_md', 'design_bottom_md', 'approved_by'],
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
    "image": {
        "label": "影像上传",
        "icon": "▧",
        "table": "images",
        "desc": "上传岩心表面、展开、荧光、岩心箱或薄片影像；文件写入本地/MinIO。",
        "list_fields": ["well_id", "type", "top_md", "bottom_md", "captured_at"],
        "label_expr": "COALESCE(type,'影像') || ' / #' || CAST(id AS text)",
        "fields": [
            _f("well_id", "所属井", "select", True, options={"kind": "wells"}),
            _f("run_id", "回次", "select", options={"kind": "runs"}),
            _f("section_id", "岩心段", "select", options={"kind": "sections"}),
            _f("type", "影像类型", "select", True, options=["SURFACE", "ROLLED", "FLUORESCENCE", "BOX", "THIN_SECTION"]),
            _f("light", "光性", placeholder="自然光 / 紫外光"),
            _f("top_md", "顶深", "number"),
            _f("bottom_md", "底深", "number"),
            _f("captured_at", "拍摄时间", "date"),
            _f("device", "设备"),
            _f("operator", "操作人"),
            _f("quality", "质量", placeholder="合格 / 可疑"),
        ],
    },
    "description": {
        "label": "岩心描述",
        "icon": "◇",
        "table": "core_description",
        "desc": "按区间记录，可多次观察、保留版本；同一段允许多条描述。",
        "list_fields": ["section_id", "interval_top_md", "interval_bottom_md", "description_type", "version", "is_current"],
        "label_expr": "'段 ' || CAST(section_id AS text) || ' / v' || CAST(version AS text)",
        "fields": [
            _f("section_id", "岩心段", "select", True, options={"kind": "sections"}),
            _f("interval_top_md", "描述顶深", "number", placeholder="留空按岩心段"),
            _f("interval_bottom_md", "描述底深", "number", placeholder="留空按岩心段"),
            _f("description_type", "描述类型", "select", options=["综合观察", "补充观察", "岩心描述"]),
            _f("version", "版本", "int", placeholder="默认 1"),
            _f("is_current", "当前版本", "select", options=[{"value": "1", "label": "当前版本"}, {"value": "0", "label": "历史版本"}]),
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
    "core_analysis": {
        "label": "分析数据集",
        "icon": "▦",
        "table": "core_analysis",
        "desc": "一口井可以有多套分析数据/复测版本；批次挂在数据集下。",
        "list_fields": ["well_id", "name", "lab", "version", "is_current", "analysis_date"],
        "label_expr": "name || ' / v' || CAST(version AS text)",
        "fields": [
            _f("well_id", "所属井", "select", True, options={"kind": "wells"}),
            _f("name", "数据集名称", required=True, placeholder="例如 历史分析"),
            _f("lab", "实验室"),
            _f("analysis_date", "分析日期", "date"),
            _f("depth_shift_m", "深度校正", "number", placeholder="m"),
            _f("version", "版本", "int", placeholder="默认 1"),
            _f("is_current", "当前数据集", "select", options=[{"value": "1", "label": "当前"}, {"value": "0", "label": "历史"}]),
            _f("remark", "备注", "textarea", wide=True),
        ],
    },
    "analysis_batch": {
        "label": "实验批次",
        "icon": "⌁",
        "table": "analysis_batch",
        "desc": "同一实验室、方法、日期的样品放在一个批次里。",
        "list_fields": ["core_analysis_id", "batch_no", "lab", "method", "analysis_date", "qc_status"],
        "label_expr": "batch_no",
        "fields": [
            _f("core_analysis_id", "分析数据集", "select", True, options={"kind": "analyses"}),
            _f("batch_no", "批次号", required=True, placeholder="例如 LAB-2026-001"),
            _f("lab", "实验室"),
            _f("method", "方法/标准"),
            _f("analysis_date", "分析日期", "date"),
            _f("qc_status", "质控状态", "select", options=["待检", "合格", "可疑"]),
            _f("remark", "备注", "textarea", wide=True),
        ],
    },
    "analysis_result": {
        "label": "实验结果",
        "icon": "∑",
        "table": "analysis_result",
        "desc": "一个批次下的样品实验结果，一行一个参数。",
        "list_fields": ["batch_id", "sample_id", "test_type", "param", "value", "unit", "quality"],
        "label_expr": "test_type || ' / ' || COALESCE(param,'')",
        "fields": [
            _f("batch_id", "实验批次", "select", True, options={"kind": "batches"}),
            _f("sample_id", "样品", "select", True, options={"kind": "samples"}),
            _f("test_type", "实验类型", required=True, placeholder="例如 孔隙度"),
            _f("analysis_group", "分析大类", "select", options={"kind": "dict", "type": "analysis_group"}),
            _f("param", "参数"),
            _f("value", "数值", "number"),
            _f("unit", "单位"),
            _f("detection_limit", "检出限"),
            _f("quality", "质量", placeholder="合格 / 可疑"),
            _f("test_date", "实验日期", "date"),
        ],
    },
}

HIDDEN = set()
ORDER = ["well", "run", "section", "description", "fracture", "vug", "sidewall",
         "sample", "core_analysis", "analysis_batch", "analysis_result",
         "coring_plan", "image"]


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
    analyses = _rows(conn, """SELECT a.id, a.well_id, a.name, a.version,
        w.code || ' / ' || a.name || ' / v' || CAST(a.version AS text) AS label
        FROM core_analysis a JOIN wells w ON w.id=a.well_id ORDER BY w.code, a.id""")
    batches = _rows(conn, """SELECT b.id, b.well_id, b.core_analysis_id, b.batch_no,
        b.batch_no || ' / ' || COALESCE(b.lab,'') AS label
        FROM analysis_batch b ORDER BY b.id DESC""")
    dicts = {}
    for r in _rows(conn, "SELECT dict_type, code, name FROM dictionary ORDER BY dict_type, sort_no, code"):
        dicts.setdefault(r["dict_type"], []).append({"value": r["code"], "label": r["name"]})
    return {"wells": wells, "runs": runs, "sections": sections,
            "sidewalls": sidewalls, "samples": samples, "analyses": analyses,
            "batches": batches, "dicts": dicts}


def meta(conn):
    keys = [k for k in ORDER if k in ENTITIES and k not in HIDDEN]
    keys += [k for k in ENTITIES if k not in keys and k not in HIDDEN]
    return {"entities": [
        {"key": k, "label": ENTITIES[k]["label"], "icon": ENTITIES[k].get("icon", ""),
         "desc": ENTITIES[k].get("desc", ""), "fields": ENTITIES[k]["fields"]}
        for k in keys
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
    elif isinstance(opt, list):
        allowed = [x.get("value") if isinstance(x, dict) else x for x in opt]
        if value not in allowed:
            raise EntryError(f"{field['label']}取值不正确", 400)


def records(conn, entity, limit=40, deleted=False):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    wanted = spec.get("list_fields", [f["name"] for f in spec["fields"][:4]])
    fields = [f for f in spec["fields"] if f["name"] in wanted]
    cols = ["id"] + [f["name"] for f in fields]
    where = "WHERE deleted_at IS NOT NULL" if deleted else "WHERE deleted_at IS NULL"
    sql = f'SELECT {", ".join(cols)} FROM {spec["table"]} {where} ORDER BY id DESC LIMIT ?'
    items = _rows(conn, sql, (int(limit),))
    total = _one(conn, f'SELECT COUNT(*) AS c FROM {spec["table"]} {where}')["c"]
    return {"entity": entity, "label": spec["label"], "total": total, "deleted": bool(deleted),
            "fields": [{"name": "id", "label": "ID"}] + [{"name": f["name"], "label": f["label"]} for f in fields],
            "items": items}


def get_record(conn, entity, rid):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    row = _one(conn, f'SELECT * FROM {spec["table"]} WHERE id=?', (rid,))
    if not row:
        raise EntryError("记录不存在", 404)
    return {"entity": entity, "label": spec["label"], "record": row}


def _unique(conn, entity, data, rid=None):
    checks = {
        "well": ("SELECT 1 AS ok FROM wells WHERE code=? AND id<>?", ("code",)),
        "run": ("SELECT 1 AS ok FROM runs WHERE well_id=? AND run_no=? AND id<>?", ("well_id", "run_no")),
        "section": ("SELECT 1 AS ok FROM sections WHERE run_id=? AND section_no=? AND id<>?", ("run_id", "section_no")),
        "sidewall": ("SELECT 1 AS ok FROM core_sidewall WHERE sample_no=? AND id<>?", ("sample_no",)),
        "sample": ("SELECT 1 AS ok FROM samples WHERE sample_no=? AND id<>?", ("sample_no",)),
        "coring_plan": ("SELECT 1 AS ok FROM coring_plan WHERE run_id=? AND id<>?", ("run_id",)),
    }
    if entity not in checks:
        return
    sql, names = checks[entity]
    vals = [data.get(n) for n in names]
    if all(v is not None for v in vals):
        if _one(conn, sql, tuple(vals) + (rid or -1,)):
            raise EntryError("数据重复，违反唯一约束", 409)


def _mirror_update(conn, entity, rid, data):
    if not is_postgres():
        return
    if entity == "well":
        if "lon" not in data and "lat" not in data:
            return
        conn.execute("DELETE FROM well_geometry WHERE well_id=?", (rid,))
        if data.get("lon") is not None and data.get("lat") is not None:
            conn.execute("INSERT INTO well_geometry(well_id, geom) VALUES (?, ST_SetSRID(ST_MakePoint(?, ?), 4326)::geography)",
                         (rid, data["lon"], data["lat"]))
    elif entity == "run" and data.get("top_md") is not None and data.get("bottom_md") is not None:
        conn.execute("DELETE FROM run_depth WHERE run_id=?", (rid,))
        conn.execute("INSERT INTO run_depth(run_id, depth) VALUES (?, numrange(?, ?, '[)'))",
                     (rid, data["top_md"], data["bottom_md"]))
    elif entity == "section" and data.get("top_md") is not None and data.get("bottom_md") is not None:
        conn.execute("DELETE FROM section_depth WHERE section_id=?", (rid,))
        conn.execute("INSERT INTO section_depth(section_id, depth) VALUES (?, numrange(?, ?, '[)'))",
                     (rid, data["top_md"], data["bottom_md"]))


def update(conn, entity, rid, body, actor='system'):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    existing = _one(conn, f'SELECT * FROM {spec["table"]} WHERE id=?', (rid,))
    if not existing:
        raise EntryError("记录不存在", 404)

    data = {}
    for field in spec["fields"]:
        if field["name"] not in body:
            continue
        val = _convert(field, body.get(field["name"]))
        if field.get("required") and val is None:
            raise EntryError(f"请填写{field['label']}", 400)
        if val is not None:
            _check_choice(conn, field, val)
        data[field["name"]] = val

    for ref in ("well_id", "run_id", "section_id", "sidewall_id", "sample_id"):
        if ref in data:
            data[ref] = _resolve_ref(conn, ref, data[ref])

    # keep required fields that were omitted
    for field in spec["fields"]:
        if field.get("required") and field["name"] not in data and existing.get(field["name"]) is None:
            raise EntryError(f"请填写{field['label']}", 400)

    if entity == "description":
        section_id = data.get("section_id", existing["section_id"])
        sec = _one(conn, "SELECT * FROM sections WHERE id=?", (section_id,))
        if not sec:
            raise EntryError("岩心段不存在", 400)
        top = data.get("interval_top_md", existing["interval_top_md"])
        bottom = data.get("interval_bottom_md", existing["interval_bottom_md"])
        if top is None or bottom is None or bottom <= top:
            raise EntryError("描述底深必须大于顶深", 400)
        if top < (sec["top_md"] or top) - 0.001 or bottom > (sec["bottom_md"] or bottom) + 0.001:
            raise EntryError("描述区间必须在岩心段范围内", 400)
        data["section_id"], data["interval_top_md"], data["interval_bottom_md"] = section_id, top, bottom
        data.setdefault("version", existing.get("version", 1))
        data.setdefault("is_current", existing.get("is_current", 0))
        if int(data["is_current"]) == 1:
            conn.execute("UPDATE core_description SET is_current=0 WHERE section_id=? AND id<>?",
                         (section_id, rid))
    elif entity == "core_analysis":
        well_id = data.get("well_id", existing["well_id"])
        name = data.get("name", existing["name"])
        version = data.get("version", existing["version"])
        if _one(conn, "SELECT 1 AS ok FROM core_analysis WHERE well_id=? AND name=? AND version=? AND id<>?",
                (well_id, name, version, rid)):
            raise EntryError("同井、同名称、同版本的数据集已存在", 409)
        data["well_id"], data["name"], data["version"] = well_id, name, version
        data.setdefault("is_current", existing.get("is_current", 0))
        if int(data["is_current"]) == 1:
            conn.execute("UPDATE core_analysis SET is_current=0 WHERE well_id=? AND id<>?", (well_id, rid))
    elif entity == "analysis_batch":
        ca_id = data.get("core_analysis_id", existing["core_analysis_id"])
        ca = _one(conn, "SELECT * FROM core_analysis WHERE id=?", (ca_id,))
        if not ca:
            raise EntryError("分析数据集不存在", 400)
        batch_no = data.get("batch_no", existing["batch_no"])
        if _one(conn, "SELECT 1 AS ok FROM analysis_batch WHERE core_analysis_id=? AND batch_no=? AND id<>?",
                (ca_id, batch_no, rid)):
            raise EntryError("该数据集下批次号已存在", 409)
        data["core_analysis_id"], data["well_id"], data["batch_no"] = ca_id, ca["well_id"], batch_no
    elif entity == "analysis_result":
        batch_id = data.get("batch_id", existing["batch_id"])
        sample_id = data.get("sample_id", existing["sample_id"])
        if not _one(conn, "SELECT 1 AS ok FROM analysis_batch WHERE id=?", (batch_id,)):
            raise EntryError("实验批次不存在", 400)
        if not _one(conn, "SELECT 1 AS ok FROM samples WHERE id=?", (sample_id,)):
            raise EntryError("样品不存在", 400)
        data["batch_id"], data["sample_id"] = batch_id, sample_id
    if entity == "well":
        if data.get("code") and _one(conn, "SELECT 1 AS ok FROM wells WHERE code=? AND id<>?", (data["code"], rid)):
            raise EntryError("井号已存在", 409)
    elif entity == "run":
        well_id = data.get("well_id", existing["well_id"])
        run_no = data.get("run_no", existing["run_no"])
        if not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (well_id,)):
            raise EntryError("所属井不存在", 400)
        if data.get("top_md") is not None and data.get("bottom_md") is not None and data["bottom_md"] <= data["top_md"]:
            raise EntryError("底深必须大于顶深", 400)
        data["well_id"], data["run_no"] = well_id, run_no
        _unique(conn, "run", data, rid)
    elif entity == "section":
        run_id = data.get("run_id", existing["run_id"])
        run = _one(conn, "SELECT * FROM runs WHERE id=?", (run_id,))
        if not run:
            raise EntryError("所属回次不存在", 400)
        data["run_id"] = run_id
        data["well_id"] = run["well_id"]
        top_md = data.get("top_md", existing.get("top_md"))
        bottom_md = data.get("bottom_md", existing.get("bottom_md"))
        if top_md is not None and bottom_md is not None and bottom_md <= top_md:
            raise EntryError("底深必须大于顶深", 400)
        data["top_md"], data["bottom_md"] = top_md, bottom_md
        if data.get("length") is None and top_md is not None and bottom_md is not None:
            data["length"] = round(bottom_md - top_md, 3)
        section_no = data.get("section_no", existing["section_no"])
        data["section_no"] = section_no
        _unique(conn, "section", data, rid)
    elif entity in ("fracture", "vug"):
        section_id = data.get("section_id", existing["section_id"])
        if not _one(conn, "SELECT 1 AS ok FROM sections WHERE id=?", (section_id,)):
            raise EntryError("岩心段不存在", 400)
        data["section_id"] = section_id
    elif entity == "sidewall":
        if data.get("well_id") and not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (data["well_id"],)):
            raise EntryError("所属井不存在", 400)
        if data.get("sample_no"):
            _unique(conn, "sidewall", data, rid)
    elif entity == "sample":
        if data.get("parent_sample_id"):
            parent = _one(conn, "SELECT * FROM samples WHERE id=?", (data["parent_sample_id"],))
            if not parent:
                raise EntryError("母样不存在", 400)
            data["well_id"] = parent["well_id"]
            data["section_id"] = data.get("section_id") or parent.get("section_id")
            data["sidewall_id"] = data.get("sidewall_id") or parent.get("sidewall_id")
            data["top_md"] = data.get("top_md") if data.get("top_md") is not None else parent.get("top_md")
            data["bottom_md"] = data.get("bottom_md") if data.get("bottom_md") is not None else parent.get("bottom_md")
        section_id = data.get("section_id", existing.get("section_id"))
        sidewall_id = data.get("sidewall_id", existing.get("sidewall_id"))
        if section_id and sidewall_id:
            raise EntryError("样品只能属于岩心段或井壁取心之一", 400)
        if not section_id and not sidewall_id:
            raise EntryError("请选择岩心段或井壁取心", 400)
        if section_id:
            sec = _one(conn, "SELECT * FROM sections WHERE id=?", (section_id,))
            if not sec:
                raise EntryError("岩心段不存在", 400)
            data["section_id"], data["sidewall_id"] = section_id, None
            data["well_id"] = sec["well_id"]
            data["top_md"] = data.get("top_md", sec["top_md"])
            data["bottom_md"] = data.get("bottom_md", sec["bottom_md"])
        else:
            sw = _one(conn, "SELECT * FROM core_sidewall WHERE id=?", (sidewall_id,))
            if not sw:
                raise EntryError("井壁取心不存在", 400)
            data["section_id"], data["sidewall_id"] = None, sidewall_id
            data["well_id"] = sw["well_id"]
            data["top_md"] = data.get("top_md", sw["depth_md"])
            data["bottom_md"] = data.get("bottom_md", sw["depth_md"])
        if data.get("sample_no"):
            _unique(conn, "sample", data, rid)
    elif entity == "coring_plan":
        run_id = data.get("run_id", existing["run_id"])
        if not _one(conn, "SELECT 1 AS ok FROM runs WHERE id=?", (run_id,)):
            raise EntryError("取心回次不存在", 400)
        data["run_id"] = run_id
        _unique(conn, "coring_plan", data, rid)

    cols = list(data.keys())
    if not cols:
        raise EntryError("没有可更新的字段", 400)
    sets = ", ".join(f"{c}=?" for c in cols)
    try:
        conn.execute(f'UPDATE {spec["table"]} SET {sets} WHERE id=?', [data[c] for c in cols] + [rid])
        _mirror_update(conn, entity, rid, data)
        audit.log(conn, actor, "更新", f"{spec['label']} #{rid}", data)
        conn.commit()
    except Exception as e:
        conn.rollback()
        msg = str(e)
        if "UNIQUE" in msg.upper():
            raise EntryError("数据重复，违反唯一约束", 409)
        raise EntryError(f"更新失败：{msg[:200]}", 500)
    return {"id": rid, "entity": entity, "label": spec["label"]}


DEPENDENTS = {
    "well": [("runs", "well_id"), ("strata", "well_id"), ("sections", "well_id"),
             ("images", "well_id"), ("scans", "well_id"), ("products", "well_id"),
             ("core_sidewall", "well_id"), ("samples", "well_id"),
             ("inventory", "well_id"), ("txns", "well_id")],
    "run": [("strata", "run_id"), ("sections", "run_id"), ("images", "run_id"), ("coring_plan", "run_id")],
    "section": [("core_fracture", "section_id"),
                ("core_vug", "section_id"), ("samples", "section_id"), ("images", "section_id"),
                ("inventory", "section_id"), ("txns", "section_id"), ("annotations", "section_id")],
    "description": [],
    "core_analysis": [("analysis_batch", "core_analysis_id")],
    "analysis_batch": [("analysis_result", "batch_id")],
    "analysis_result": [],
    "fracture": [],
    "vug": [],
    "sidewall": [("samples", "sidewall_id")],
    "sample": [("analysis_result", "sample_id"), ("samples", "parent_sample_id")],
    "coring_plan": [],
    "image": [("annotations", "image_id"), ("image_calibration", "image_id"),
              ("core_fracture", "image_id"), ("core_vug", "image_id")],
}


def delete(conn, entity, rid, actor='system'):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    if not _one(conn, f'SELECT 1 AS ok FROM {spec["table"]} WHERE id=?', (rid,)):
        raise EntryError("记录不存在", 404)
    for table, col in DEPENDENTS.get(entity, []):
        n = _one(conn, f'SELECT COUNT(*) AS c FROM {table} WHERE {col}=?', (rid,))["c"]
        if n:
            raise EntryError(f"存在 {n} 条关联记录，不能删除；请先处理子记录", 409)
    try:
        conn.execute(f'UPDATE {spec["table"]} SET deleted_at=? WHERE id=?',
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid))
        audit.log(conn, actor, "删除", f"{spec['label']} #{rid}", {})
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise EntryError(f"删除失败：{str(e)[:200]}", 500)
    return {"id": rid, "entity": entity, "label": spec["label"], "deleted": True}


def restore(conn, entity, rid, actor="system"):
    spec = ENTITIES.get(entity)
    if not spec:
        raise EntryError("未知录入对象", 404)
    row = _one(conn, f'SELECT * FROM {spec["table"]} WHERE id=?', (rid,))
    if not row:
        raise EntryError("记录不存在", 404)
    if not row.get("deleted_at"):
        raise EntryError("记录未被删除", 400)
    try:
        conn.execute(f'UPDATE {spec["table"]} SET deleted_at=NULL WHERE id=?', (rid,))
        audit.log(conn, actor, "恢复", f"{spec['label']} #{rid}", {})
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise EntryError(f"恢复失败：{str(e)[:200]}", 500)
    return {"id": rid, "entity": entity, "label": spec["label"], "restored": True}


def _resolve_ref(conn, name, value):
    if value is None or isinstance(value, int):
        return value
    s = str(value).strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if name == "well_id":
        row = _one(conn, "SELECT id FROM wells WHERE code=?", (s,))
    elif name == "run_id":
        parts = re.split(r"\s*/\s*", s)
        if len(parts) >= 2:
            row = _one(conn, """SELECT r.id FROM runs r JOIN wells w ON w.id=r.well_id
                WHERE w.code=? AND r.run_no=?""", (parts[0], int(parts[1]) if parts[1].isdigit() else -1))
        else:
            row = None
    elif name == "section_id":
        parts = re.split(r"\s*/\s*", s)
        if len(parts) >= 3:
            row = _one(conn, """SELECT s.id FROM sections s JOIN runs r ON r.id=s.run_id
                JOIN wells w ON w.id=s.well_id WHERE w.code=? AND r.run_no=? AND s.section_no=?""",
                (parts[0], int(parts[1]) if parts[1].isdigit() else -1, parts[2]))
        else:
            row = None
    elif name == "sample_id":
        row = _one(conn, "SELECT id FROM samples WHERE sample_no=?", (s,))
    elif name == "sidewall_id":
        row = _one(conn, "SELECT id FROM core_sidewall WHERE sample_no=?", (s,))
    else:
        row = None
    if not row:
        raise EntryError(f"找不到关联记录：{s}", 400)
    return row["id"]

def create(conn, entity, body, actor='system', dry_run=False):
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

    for ref in ("well_id", "run_id", "section_id", "sidewall_id", "sample_id", "parent_sample_id"):
        if ref in data:
            data[ref] = _resolve_ref(conn, ref, data[ref])

    # parent checks and automatic fields
    if entity == "description":
        sec = _one(conn, "SELECT * FROM sections WHERE id=?", (data["section_id"],))
        if not sec:
            raise EntryError("岩心段不存在", 400)
        top = data.get("interval_top_md", sec["top_md"])
        bottom = data.get("interval_bottom_md", sec["bottom_md"])
        if top is None or bottom is None or bottom <= top:
            raise EntryError("描述底深必须大于顶深", 400)
        if top < (sec["top_md"] or top) - 0.001 or bottom > (sec["bottom_md"] or bottom) + 0.001:
            raise EntryError("描述区间必须在岩心段范围内", 400)
        data["interval_top_md"], data["interval_bottom_md"] = top, bottom
        data.setdefault("description_type", "综合观察")
        data.setdefault("version", 1)
        data.setdefault("is_current", 1)
        if int(data["is_current"]) == 1:
            conn.execute("UPDATE core_description SET is_current=0 WHERE section_id=?", (data["section_id"],))
    elif entity == "core_analysis":
        if not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (data["well_id"],)):
            raise EntryError("所属井不存在", 400)
        data.setdefault("version", 1)
        data.setdefault("is_current", 1)
        if _one(conn, "SELECT 1 AS ok FROM core_analysis WHERE well_id=? AND name=? AND version=?",
                (data["well_id"], data["name"], data["version"])):
            raise EntryError("同井、同名称、同版本的数据集已存在", 409)
        if int(data["is_current"]) == 1:
            conn.execute("UPDATE core_analysis SET is_current=0 WHERE well_id=?", (data["well_id"],))
    elif entity == "analysis_batch":
        ca = _one(conn, "SELECT * FROM core_analysis WHERE id=?", (data["core_analysis_id"],))
        if not ca:
            raise EntryError("分析数据集不存在", 400)
        data["well_id"] = ca["well_id"]
        if _one(conn, "SELECT 1 AS ok FROM analysis_batch WHERE core_analysis_id=? AND batch_no=?",
                (data["core_analysis_id"], data["batch_no"])):
            raise EntryError("该数据集下批次号已存在", 409)
    elif entity == "analysis_result":
        if not _one(conn, "SELECT 1 AS ok FROM analysis_batch WHERE id=?", (data["batch_id"],)):
            raise EntryError("实验批次不存在", 400)
        if not _one(conn, "SELECT 1 AS ok FROM samples WHERE id=?", (data["sample_id"],)):
            raise EntryError("样品不存在", 400)
    elif entity == "image":
        raise EntryError("请使用影像上传按钮", 400)
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
    elif entity in ("fracture", "vug"):
        if not _one(conn, "SELECT 1 AS ok FROM sections WHERE id=?", (data["section_id"],)):
            raise EntryError("岩心段不存在", 400)
    elif entity == "sidewall":
        if not _one(conn, "SELECT 1 AS ok FROM wells WHERE id=?", (data["well_id"],)):
            raise EntryError("所属井不存在", 400)
        if _one(conn, "SELECT 1 AS ok FROM core_sidewall WHERE sample_no=?", (data["sample_no"],)):
            raise EntryError("井壁取心样品号已存在", 409)
    elif entity == "sample":
        parent = None
        if data.get("parent_sample_id"):
            parent = _one(conn, "SELECT * FROM samples WHERE id=?", (data["parent_sample_id"],))
            if not parent:
                raise EntryError("母样不存在", 400)
            data["well_id"] = parent["well_id"]
            data["section_id"] = data.get("section_id") or parent.get("section_id")
            data["sidewall_id"] = data.get("sidewall_id") or parent.get("sidewall_id")
            data["top_md"] = data.get("top_md") if data.get("top_md") is not None else parent.get("top_md")
            data["bottom_md"] = data.get("bottom_md") if data.get("bottom_md") is not None else parent.get("bottom_md")
        if data.get("section_id") and data.get("sidewall_id"):
            raise EntryError("样品只能属于岩心段或井壁取心之一", 400)
        if not data.get("section_id") and not data.get("sidewall_id"):
            raise EntryError("请选择岩心段、井壁取心或母样", 400)
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
    elif entity == "coring_plan":
        if not _one(conn, "SELECT 1 AS ok FROM runs WHERE id=?", (data["run_id"],)):
            raise EntryError("取心回次不存在", 400)
        if _one(conn, "SELECT 1 AS ok FROM coring_plan WHERE run_id=?", (data["run_id"],)):
            raise EntryError("该回次已有取心设计", 409)

    if dry_run:
        return {"id": None, "entity": entity, "label": spec["label"], "dry_run": True}

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
        audit.log(conn, actor, "新增", f"{spec['label']} #{new_id}", data)
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
