# -*- coding: utf-8 -*-
"""Create chart template / well chart tables and backfill existing products."""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "core.db"

CATEGORIES = [
    ("BASIC", "基本图", 1),
    ("COMPOSITE", "综合图", 2),
    ("FLUOR", "荧光图切", 3),
    ("CUTTINGS", "岩屑综合图", 4),
    ("MULTI", "多井对比", 5),
    ("BOREHOLE", "钻孔柱状图", 6),
    ("LAYER", "岩心层模板", 7),
    ("DELIVERABLE", "成果", 8),
]

TEMPLATES = [
    # code, name, category, version, project, output, active, sort
    ("CORE_BASIC", "岩心基本图", "BASIC", "V1", "", "交互图", 1, 1),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V1", "", "交互图", 1, 2),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V8", "", "交互图", 1, 3),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V10", "", "交互图", 1, 4),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V10", "克拉玛依", "交互图", 1, 5),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V1", "青海", "交互图", 1, 6),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V10", "冀塔", "交互图", 1, 7),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V10", "扬州石化", "交互图", 1, 8),
    ("CORE_COMPOSITE", "岩心综合图", "COMPOSITE", "V1", "中油测井天津", "交互图", 1, 9),
    ("FLUORESCENCE", "荧光图切", "FLUOR", "V1", "", "交互图", 1, 10),
    ("CUTTINGS_COMPOSITE", "岩屑综合图", "CUTTINGS", "V1", "", "交互图", 1, 11),
    ("MULTI_WELL", "多井对比", "MULTI", "V1", "", "交互图", 1, 12),
    ("BOREHOLE_COLUMN", "钻孔柱状图", "BOREHOLE", "V1", "", "交互图", 1, 13),
    ("CORE_LAYER", "岩心层模板", "LAYER", "V03", "", "交互图", 1, 14),
    ("EXP_RESULT", "实验成果", "DELIVERABLE", "V1", "", "文件", 1, 15),
    ("IMAGE_RESULT", "影像成果", "DELIVERABLE", "V1", "", "文件", 1, 16),
    ("STOCK_RESULT", "库存成果", "DELIVERABLE", "V1", "", "文件", 1, 17),
]

PRODUCT_MAP = {
    "COLUMN": ("CORE_COMPOSITE", "V1", ""),
    "EXP": ("EXP_RESULT", "V1", ""),
    "FLUOR": ("FLUORESCENCE", "V1", ""),
    "IMAGE": ("IMAGE_RESULT", "V1", ""),
    "MULTI": ("MULTI_WELL", "V1", ""),
    "STOCK": ("STOCK_RESULT", "V1", ""),
}


def main():
    if not DB_PATH.exists():
        print("DB not found", DB_PATH)
        return
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS chart_category (code TEXT PRIMARY KEY, name TEXT NOT NULL, sort_no INTEGER DEFAULT 0)")
    con.execute("""CREATE TABLE IF NOT EXISTS chart_template (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL, name TEXT NOT NULL, category_code TEXT NOT NULL,
        version TEXT DEFAULT '', project TEXT DEFAULT '', output_type TEXT DEFAULT '交互图',
        config_json TEXT DEFAULT '{}', is_active INTEGER DEFAULT 1, sort_no INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(code, version, project))""")
    con.execute("""CREATE TABLE IF NOT EXISTS well_chart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        well_id INTEGER NOT NULL, template_id INTEGER NOT NULL,
        status TEXT DEFAULT '未生成', file_url TEXT, image_url TEXT,
        generated_at TEXT, generated_by TEXT, error_msg TEXT,
        UNIQUE(well_id, template_id))""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_chart_template_cat ON chart_template(category_code)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_well_chart_well ON well_chart(well_id)")
    for code, name, sort in CATEGORIES:
        con.execute("INSERT OR IGNORE INTO chart_category(code,name,sort_no) VALUES(?,?,?)", (code, name, sort))
    for code, name, cat, ver, project, output, active, sort in TEMPLATES:
        con.execute("""INSERT OR IGNORE INTO chart_template
            (code,name,category_code,version,project,output_type,config_json,is_active,sort_no)
            VALUES(?,?,?,?,?,?, '{}', ?, ?)""",
            (code, name, cat, ver, project, output, active, sort))
    # backfill existing products
    for p in con.execute("SELECT well_id, code, status FROM products").fetchall():
        target = PRODUCT_MAP.get(p["code"])
        if not target:
            continue
        code, ver, project = target
        t = con.execute("""SELECT id FROM chart_template
            WHERE code=? AND version=? AND project=?""", (code, ver, project)).fetchone()
        if not t:
            continue
        status = "已生成" if str(p["status"]).lower() in ("done", "已生成") else "未生成"
        con.execute("""INSERT OR IGNORE INTO well_chart
            (well_id,template_id,status,generated_at,generated_by)
            VALUES(?,?,?,datetime('now'),'system')""", (p["well_id"], t["id"], status))
    con.commit()
    print("chart tables", con.execute("SELECT COUNT(*) FROM chart_template").fetchone()[0],
          con.execute("SELECT COUNT(*) FROM well_chart").fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
