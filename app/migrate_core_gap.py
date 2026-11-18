# -*- coding: utf-8 -*-
"""Apply the core-data supplement and populate a small demo set."""
import argparse
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "data" / "core.db"
DDL = BASE / "migrations" / "001_core_gap.sql"


def columns(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}


def add_column(conn, table, name, decl):
    if name not in columns(conn, table):
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {decl}')


def main():
    ap = argparse.ArgumentParser(description="Apply core-gap migration and demo rows")
    ap.add_argument("--reset", action="store_true", help="clear and repopulate supplement tables")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL.read_text(encoding="utf-8"))

    # additive columns on existing tables
    add_column(conn, "experiments", "sample_id", "INTEGER")
    add_column(conn, "experiments", "analysis_group", "TEXT")
    add_column(conn, "experiments", "method", "TEXT")
    add_column(conn, "experiments", "detection_limit", "TEXT")
    add_column(conn, "experiments", "quality", "TEXT")
    add_column(conn, "annotations", "shape_type", "TEXT")
    add_column(conn, "annotations", "section_id", "INTEGER")
    add_column(conn, "annotations", "area", "REAL")
    add_column(conn, "annotations", "length", "REAL")
    add_column(conn, "annotations", "angle", "REAL")
    add_column(conn, "annotations", "model_version", "TEXT")

    # indexes for tree traversal
    for sql in [
        "CREATE INDEX IF NOT EXISTS idx_core_obs_section ON core_observation(section_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_frac_section ON core_fracture(section_id)",
        "CREATE INDEX IF NOT EXISTS idx_core_vug_section ON core_vug(section_id)",
        "CREATE INDEX IF NOT EXISTS idx_sw_well ON core_sidewall(well_id)",
        "CREATE INDEX IF NOT EXISTS idx_samples_section ON samples(section_id)",
        "CREATE INDEX IF NOT EXISTS idx_samples_sidewall ON samples(sidewall_id)",
        "CREATE INDEX IF NOT EXISTS idx_exp_sample ON experiments(sample_id)",
        "CREATE INDEX IF NOT EXISTS idx_cal_image ON image_calibration(image_id)",
        "CREATE INDEX IF NOT EXISTS idx_anno_image ON annotations(image_id)",
        "CREATE INDEX IF NOT EXISTS idx_plan_run ON coring_plan(run_id)",
    ]:
        conn.execute(sql)

    # dictionary seed
    dicts = [
        ("structure", "CLASTIC", "碎屑结构", "", 1),
        ("structure", "MUDDY", "泥质结构", "", 2),
        ("structure", "CRYSTAL", "晶粒结构", "", 3),
        ("structure", "BIO", "生物结构", "", 4),
        ("sedimentary_structure", "MASSIVE", "块状层理", "", 1),
        ("sedimentary_structure", "PARALLEL", "平行层理", "", 2),
        ("sedimentary_structure", "CROSS", "交错层理", "", 3),
        ("sedimentary_structure", "GRADED", "递变层理", "", 4),
        ("contact", "CONFORM", "整合", "", 1),
        ("contact", "UNCONFORM", "不整合", "", 2),
        ("contact", "FAULT", "断层接触", "", 3),
        ("fossil", "NONE", "未见", "", 1),
        ("fossil", "TRACE", "少量生物碎屑", "", 2),
        ("fossil", "RICH", "化石富集", "", 3),
        ("gas_show", "NONE", "无", "", 1),
        ("gas_show", "LOG_ANOMALY", "气测异常", "", 2),
        ("gas_show", "KICK", "气侵", "", 3),
        ("gas_show", "GAS_LAYER", "气层", "", 4),
        ("breakage_wear", "INTACT", "完整", "", 1),
        ("breakage_wear", "SLIGHT", "轻微磨损", "", 2),
        ("breakage_wear", "BROKEN", "破碎", "", 3),
        ("analysis_group", "PHYSICAL", "物性", "", 1),
        ("analysis_group", "GEOCHEM", "地化", "", 2),
        ("analysis_group", "MINERAL", "岩石矿物", "", 3),
        ("analysis_group", "PALEO", "古生物", "", 4),
        ("analysis_group", "FLUID", "油气水性质", "", 5),
        ("analysis_group", "PVT", "高压物性", "", 6),
        ("analysis_group", "DEV_TEST", "开发试验", "", 7),
        ("fracture_type", "OPEN", "张开缝", "", 1),
        ("fracture_type", "CLOSED", "闭合缝", "", 2),
        ("fracture_type", "FILLED", "充填缝", "", 3),
        ("fracture_type", "STYLOLITE", "压溶缝", "", 4),
        ("vug_type", "PRIMARY", "原生孔", "", 1),
        ("vug_type", "SECONDARY", "次生孔", "", 2),
        ("vug_type", "DISSOLVED", "溶蚀孔", "", 3),
        ("vug_type", "INTERGRANULAR", "粒间孔", "", 4),
        ("fill", "NONE", "无充填", "", 1),
        ("fill", "CALCITE", "方解石", "", 2),
        ("fill", "QUARTZ", "石英", "", 3),
        ("fill", "MUD", "泥质", "", 4),
        ("fill", "BITUMEN", "沥青", "", 5),
        ("sample_type", "PLUG", "柱塞样", "", 1),
        ("sample_type", "THIN", "薄片", "", 2),
        ("sample_type", "POWDER", "粉末", "", 3),
        ("sample_type", "FULL", "全直径", "", 4),
        ("sample_type", "SIDEWALL", "井壁样", "", 5),
    ]
    conn.executemany("INSERT OR IGNORE INTO dictionary(dict_type,code,name,parent_code,sort_no) VALUES(?,?,?,?,?)", dicts)

    if args.reset:
        for t in ("core_observation", "core_fracture", "core_vug", "core_sidewall",
                  "samples", "coring_plan", "image_calibration"):
            conn.execute(f'DELETE FROM "{t}"')

    now = "2026-11-17 18:00:00"
    sections = list(conn.execute("SELECT * FROM sections ORDER BY id"))
    runs = list(conn.execute("SELECT * FROM runs ORDER BY id"))
    wells = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM wells")}

    if conn.execute("SELECT COUNT(*) FROM coring_plan").fetchone()[0] == 0:
        for r in runs:
            conn.execute("""INSERT OR IGNORE INTO coring_plan
                (run_id,purpose,principle,design_top_md,design_bottom_md,design_footage,
                 design_core_length,change_reason,approved_by,approved_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (r["id"], "查明储层岩性、物性、含油性，满足取心资料要求",
                 "取全取准岩心，按设计井段连续取心；见油气显示及时调整",
                 r["top_md"], r["bottom_md"], r["footage"], r["core_length"],
                 "无", "李娜", "2026-11-10"))

    if conn.execute("SELECT COUNT(*) FROM core_observation").fetchone()[0] == 0:
        for s in sections:
            lith = s["lithology"] or ""
            if "泥" in lith:
                structure_code, structure_desc = "MUDDY", "泥质结构，质地较均一"
            elif "灰" in lith or "白云" in lith:
                structure_code, structure_desc = "CRYSTAL", "晶粒结构，局部见溶蚀"
            else:
                structure_code, structure_desc = "CLASTIC", "碎屑结构，分选中等"
            sed_code = "PARALLEL" if ("砂" in lith or "砾" in lith) else "MASSIVE"
            sed_desc = "平行层理，层间见细纹层" if sed_code == "PARALLEL" else "块状层理，未见明显层理"
            has_fracture = s["id"] % 3 == 0
            has_vug = ("灰" in lith or "白云" in lith or s["id"] % 4 == 0)
            condition = s["condition"] or ""
            if condition == "完整":
                wear = "INTACT"
            elif condition in ("较完整", "轻微破碎"):
                wear = "SLIGHT"
            else:
                wear = "BROKEN"
            gas = "LOG_ANOMALY" if "油" in (s["oil_show"] or "") else "NONE"
            conn.execute("""INSERT OR IGNORE INTO core_observation
                (section_id,structure_code,structure_desc,sedimentary_structure_code,
                 sedimentary_structure_desc,fracture_desc,fracture_density,fracture_angle,
                 vug_desc,vug_size_mm,vug_area_pct,contact_relation_code,fossil_desc,
                 dip_angle,gas_show_code,breakage_wear_code,observer,observed_at,remark)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s["id"], structure_code, structure_desc, sed_code, sed_desc,
                 "局部发育高角度构造缝" if has_fracture else "未见明显裂缝",
                 1.2 if has_fracture else 0.0, 72.0 if has_fracture else None,
                 "见少量溶蚀孔洞" if has_vug else "未见明显孔洞",
                 2.5 if has_vug else None, 0.8 if has_vug else None,
                 "CONFORM", "TRACE" if ("灰" in lith or "白云" in lith) else "NONE",
                 float(3 + (s["id"] % 8)), gas, wear, "张伟", now, "演示补充数据"))

    if conn.execute("SELECT COUNT(*) FROM core_fracture").fetchone()[0] == 0:
        for s in sections:
            if s["id"] % 3:
                continue
            conn.execute("""INSERT INTO core_fracture
                (section_id,fracture_no,type_code,dip_angle,strike_angle,length_mm,width_mm,
                 fill_code,density_per_m,image_id,geometry,description,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s["id"], f"F-{s['section_no']}-01", "构造缝", 72.0, 120.0,
                 80.0, 0.5, "方解石", 1.2, None, None,
                 "高角度构造缝，方解石半充填", now))

    if conn.execute("SELECT COUNT(*) FROM core_vug").fetchone()[0] == 0:
        for s in sections:
            lith = s["lithology"] or ""
            if not ("灰" in lith or "白云" in lith or s["id"] % 4 == 0):
                continue
            conn.execute("""INSERT INTO core_vug
                (section_id,vug_no,type_code,size_mm,area_mm2,area_pct,fill_code,
                 image_id,geometry,description,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (s["id"], f"V-{s['section_no']}-01", "溶蚀孔", 2.5, 4.9, 0.8,
                 "未充填", None, None, "溶蚀孔，局部连通", now))

    if conn.execute("SELECT COUNT(*) FROM core_sidewall").fetchone()[0] == 0:
        for w in wells.values():
            count = min(int(w["sidewall"] or 0), 4)
            if count <= 0:
                continue
            first = conn.execute("SELECT * FROM runs WHERE well_id=? ORDER BY run_no LIMIT 1", (w["id"],)).fetchone()
            base = first["top_md"] if first else (w["final_depth"] - 10)
            for i in range(count):
                conn.execute("""INSERT OR IGNORE INTO core_sidewall
                    (well_id,depth_md,sample_no,lithology,description,oil_show,fluorescence,
                     image_id,analysis_summary,collected_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (w["id"], base + i * 0.5, f"SW-{w['code']}-{i+1:02d}",
                     (first["lithology"] if first else "细砂岩"),
                     "井壁取心，岩心较完整，见油斑", "油斑", "2级",
                     None, "待送样", "2026-11-12"))

    if conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 0:
        for e in conn.execute("""SELECT sample_code, well_id, sample_type,
            MIN(top_md) top_md, MAX(bottom_md) bottom_md
            FROM experiments WHERE sample_code IS NOT NULL AND sample_code!=''
            GROUP BY sample_code, well_id, sample_type ORDER BY MIN(id)"""):
            sec = conn.execute("SELECT id FROM sections WHERE well_id=? ORDER BY id LIMIT 1", (e["well_id"],)).fetchone()
            conn.execute("""INSERT OR IGNORE INTO samples
                (sample_no,well_id,section_id,sidewall_id,sample_type,top_md,bottom_md,
                 collected_at,keeper,status)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (e["sample_code"], e["well_id"], sec["id"] if sec else None, None,
                 e["sample_type"] or "常规", e["top_md"], e["bottom_md"],
                 "2026-11-12", "李娜", "已入库"))

    # link experiments to samples + classify analysis
    sample_map = {r["sample_no"]: r["id"] for r in conn.execute("SELECT id,sample_no FROM samples")}
    group_map = {
        "孔隙度": "物性", "渗透率": "物性", "含水饱和度": "物性",
        "有机碳": "地化", "碳酸盐含量": "地化",
        "粒度中值": "岩石矿物",
    }
    for e in conn.execute("SELECT id,sample_code,test_type FROM experiments"):
        conn.execute("UPDATE experiments SET sample_id=?, analysis_group=?, method=?, detection_limit=?, quality=? WHERE id=?",
                     (sample_map.get(e["sample_code"]), group_map.get(e["test_type"], "其他"),
                      "SY/T 标准方法", "—", "合格", e["id"]))

    if conn.execute("SELECT COUNT(*) FROM image_calibration").fetchone()[0] == 0:
        for im in conn.execute("SELECT * FROM images WHERE type='SURFACE'"):
            pts = json.dumps([
                {"x": 0, "md": im["top_md"]},
                {"x": im["width"], "md": im["bottom_md"]},
            ], ensure_ascii=False)
            conn.execute("""INSERT INTO image_calibration
                (image_id,method,control_points,pixel_per_mm,residual_px,residual_mm,
                 version,operator,calibrated_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (im["id"], "标尺+两端控制点", pts,
                 1.0 / im["mm_per_px"] if im["mm_per_px"] else None,
                 0.2, 0.02, "v1", im["operator"], now))

    # existing annotations become explicit line shapes at section level
    conn.execute("""UPDATE annotations
        SET shape_type=COALESCE(shape_type,'line'),
            length=COALESCE(length,value),
            section_id=COALESCE(section_id,(SELECT section_id FROM images WHERE images.id=annotations.image_id)),
            model_version=COALESCE(model_version,'manual')
        WHERE type='length'""")

    conn.commit()
    counts = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
              for t in ("core_observation", "core_fracture", "core_vug", "core_sidewall",
                        "samples", "coring_plan", "image_calibration", "dictionary")}
    print("migration applied", counts)
    conn.close()


if __name__ == "__main__":
    main()
