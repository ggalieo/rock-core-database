# -*- coding: utf-8 -*-
"""Move the demo to a mainstream core hierarchy.

well -> core_analysis -> core_run -> core_interval
     -> core_description (N versions)
     -> sample (parent_sample)
     -> analysis_batch -> analysis_result
     -> image / storage
report_template -> report_output (separate output layer)
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "core.db"

DESC_COLS = [
    "structure_code", "structure_desc", "sedimentary_structure_code",
    "sedimentary_structure_desc", "fracture_desc", "fracture_density",
    "fracture_angle", "vug_desc", "vug_size_mm", "vug_area_pct",
    "contact_relation_code", "fossil_desc", "dip_angle", "gas_show_code",
    "breakage_wear_code", "observer", "observed_at", "remark", "deleted_at",
]


def table_exists(con, name):
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def columns(con, table):
    return {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}


def add_col(con, table, name, decl):
    if table_exists(con, table) and name not in columns(con, table):
        con.execute(f'ALTER TABLE "{table}" ADD COLUMN {name} {decl}')


def main():
    if not DB_PATH.exists():
        print("DB not found", DB_PATH)
        return
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")

    con.execute("""CREATE TABLE IF NOT EXISTS core_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        well_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        lab TEXT,
        analysis_date TEXT,
        depth_shift_m REAL DEFAULT 0,
        version INTEGER DEFAULT 1,
        is_current INTEGER DEFAULT 1,
        remark TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted_at TEXT,
        UNIQUE(well_id, name, version))""")

    con.execute("""CREATE TABLE IF NOT EXISTS core_description (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER NOT NULL,
        interval_top_md REAL NOT NULL,
        interval_bottom_md REAL NOT NULL,
        description_type TEXT DEFAULT '综合观察',
        version INTEGER DEFAULT 1,
        is_current INTEGER DEFAULT 1,
        structure_code TEXT, structure_desc TEXT,
        sedimentary_structure_code TEXT, sedimentary_structure_desc TEXT,
        fracture_desc TEXT, fracture_density REAL, fracture_angle REAL,
        vug_desc TEXT, vug_size_mm REAL, vug_area_pct REAL,
        contact_relation_code TEXT, fossil_desc TEXT, dip_angle REAL,
        gas_show_code TEXT, breakage_wear_code TEXT,
        observer TEXT, observed_at TEXT, remark TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_desc_section ON core_description(section_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_desc_current ON core_description(section_id,is_current)")

    add_col(con, "samples", "parent_sample_id", "INTEGER")
    add_col(con, "samples", "derived_reason", "TEXT")

    con.execute("""CREATE TABLE IF NOT EXISTS analysis_batch (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        core_analysis_id INTEGER NOT NULL,
        well_id INTEGER NOT NULL,
        batch_no TEXT NOT NULL,
        lab TEXT,
        method TEXT,
        analysis_date TEXT,
        qc_status TEXT,
        remark TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted_at TEXT,
        UNIQUE(core_analysis_id, batch_no))""")

    con.execute("""CREATE TABLE IF NOT EXISTS analysis_result (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        sample_id INTEGER,
        legacy_experiment_id INTEGER UNIQUE,
        test_type TEXT NOT NULL,
        analysis_group TEXT,
        param TEXT,
        value REAL,
        unit TEXT,
        detection_limit TEXT,
        quality TEXT,
        test_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted_at TEXT)""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_analysis_batch ON analysis_batch(core_analysis_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_analysis_result_batch ON analysis_result(batch_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_analysis_result_sample ON analysis_result(sample_id)")

    con.execute("""CREATE TABLE IF NOT EXISTS report_category (
        code TEXT PRIMARY KEY, name TEXT NOT NULL, sort_no INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS report_template (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL, name TEXT NOT NULL, category_code TEXT NOT NULL,
        version TEXT DEFAULT '', project TEXT DEFAULT '', output_type TEXT DEFAULT '交互图',
        config_json TEXT DEFAULT '{}', is_active INTEGER DEFAULT 1, sort_no INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(code, version, project))""")
    con.execute("""CREATE TABLE IF NOT EXISTS report_output (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        well_id INTEGER NOT NULL, template_id INTEGER NOT NULL,
        status TEXT DEFAULT '未生成', file_url TEXT, image_url TEXT,
        generated_at TEXT, generated_by TEXT, error_msg TEXT,
        UNIQUE(well_id, template_id))""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_report_output_well ON report_output(well_id)")

    # 1) observations -> descriptions (N-capable, v1 current)
    if table_exists(con, "core_observation"):
        cols = ", ".join(DESC_COLS)
        select_cols = ", ".join(f"o.{c}" for c in DESC_COLS)
        con.execute(f"""INSERT INTO core_description
            (section_id, interval_top_md, interval_bottom_md, description_type, version, is_current, {cols})
            SELECT o.section_id, s.top_md, s.bottom_md, '综合观察', 1, 1, {select_cols}
            FROM core_observation o JOIN sections s ON s.id=o.section_id
            WHERE NOT EXISTS (SELECT 1 FROM core_description d
                WHERE d.section_id=o.section_id AND d.version=1)""")

    # 2) one default core analysis per well
    for w in con.execute("SELECT id FROM wells").fetchall():
        con.execute("""INSERT OR IGNORE INTO core_analysis(well_id,name,version,is_current)
            VALUES(?,?,?,?)""", (w["id"], "历史分析", 1, 1))

    # 3) experiments -> batches/results
    if table_exists(con, "experiments"):
        exp_cols = columns(con, "experiments")
        groups = con.execute("""SELECT well_id, COALESCE(lab,'') lab, COALESCE(test_date,'') test_date
            FROM experiments GROUP BY well_id, lab, test_date ORDER BY well_id, test_date""").fetchall()
        for i, g in enumerate(groups, 1):
            ca = con.execute("SELECT id FROM core_analysis WHERE well_id=? AND version=1",
                             (g["well_id"],)).fetchone()
            if not ca:
                continue
            batch_no = f"LEG-{g['well_id']}-{i:03d}"
            con.execute("""INSERT OR IGNORE INTO analysis_batch
                (core_analysis_id,well_id,batch_no,lab,method,analysis_date,qc_status,remark)
                VALUES(?,?,?,?,?,?,?,?)""",
                (ca["id"], g["well_id"], batch_no, g["lab"], None, g["test_date"], "历史数据", "由 experiments 迁移"))
            b = con.execute("SELECT id FROM analysis_batch WHERE core_analysis_id=? AND batch_no=?",
                            (ca["id"], batch_no)).fetchone()
            if not b:
                continue
            for e in con.execute("""SELECT * FROM experiments
                WHERE well_id=? AND COALESCE(lab,'')=? AND COALESCE(test_date,'')=?""",
                (g["well_id"], g["lab"], g["test_date"])):
                con.execute("""INSERT OR IGNORE INTO analysis_result
                    (batch_id,sample_id,legacy_experiment_id,test_type,analysis_group,param,value,unit,
                     detection_limit,quality,test_date)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (b["id"], e["sample_id"], e["id"], e["test_type"],
                     e["analysis_group"] if "analysis_group" in exp_cols else None,
                     e["param"], e["value"], e["unit"],
                     e["detection_limit"] if "detection_limit" in exp_cols else None,
                     e["quality"] if "quality" in exp_cols else None, e["test_date"]))

    # 4) chart outputs -> report outputs (separate module)
    if table_exists(con, "chart_category"):
        con.execute("INSERT OR IGNORE INTO report_category(code,name,sort_no) SELECT code,name,sort_no FROM chart_category")
    if table_exists(con, "chart_template"):
        con.execute("""INSERT OR IGNORE INTO report_template
            (code,name,category_code,version,project,output_type,config_json,is_active,sort_no,created_at)
            SELECT code,name,category_code,version,project,output_type,config_json,is_active,sort_no,created_at
            FROM chart_template""")
    if table_exists(con, "well_chart"):
        con.execute("""INSERT OR IGNORE INTO report_output
            (well_id,template_id,status,file_url,image_url,generated_at,generated_by,error_msg)
            SELECT wc.well_id, rt.id, wc.status, wc.file_url, wc.image_url,
                   wc.generated_at, wc.generated_by, wc.error_msg
            FROM well_chart wc
            JOIN chart_template ct ON ct.id=wc.template_id
            JOIN report_template rt ON rt.code=ct.code AND rt.version=ct.version AND rt.project=ct.project""")

    con.commit()
    print("mainstream counts",
          "descriptions", con.execute("SELECT COUNT(*) FROM core_description").fetchone()[0],
          "analyses", con.execute("SELECT COUNT(*) FROM core_analysis").fetchone()[0],
          "batches", con.execute("SELECT COUNT(*) FROM analysis_batch").fetchone()[0],
          "results", con.execute("SELECT COUNT(*) FROM analysis_result").fetchone()[0],
          "reports", con.execute("SELECT COUNT(*) FROM report_output").fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
