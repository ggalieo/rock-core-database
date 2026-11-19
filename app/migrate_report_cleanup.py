# -*- coding: utf-8 -*-
"""Keep only the chart outputs that belong to the core archive.

The old seed contained one generic template per client/project plus three
file-only "results" (experiment/image/inventory).  Those are not core charts;
they clutter the well table and the output matrix.  This migration keeps the
seven reusable chart types and creates one output row per well/template.
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "core.db"

KEEP = {
    ("CORE_BASIC", "V1", ""),
    ("CORE_COMPOSITE", "V1", ""),
    ("FLUORESCENCE", "V1", ""),
    ("CUTTINGS_COMPOSITE", "V1", ""),
    ("MULTI_WELL", "V1", ""),
    ("BOREHOLE_COLUMN", "V1", ""),
    ("CORE_LAYER", "V03", ""),
}


def main():
    if not DB_PATH.exists():
        return
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    keep = list(KEEP)
    where = " OR ".join(["(code=? AND version=? AND project=?)"] * len(keep))
    params = [v for row in keep for v in row]

    # Remove file-only deliverables and client/project duplicates.
    con.execute(f"""DELETE FROM report_output WHERE template_id IN
        (SELECT id FROM report_template WHERE NOT ({where}))""", params)
    con.execute(f"DELETE FROM report_template WHERE NOT ({where})", params)
    con.execute("""DELETE FROM report_category WHERE code NOT IN
        (SELECT DISTINCT category_code FROM report_template)""")

    # One output row per well × kept chart type.
    con.execute("""INSERT OR IGNORE INTO report_output(well_id,template_id,status)
        SELECT w.id,t.id,'未生成' FROM wells w CROSS JOIN report_template t
        WHERE w.deleted_at IS NULL AND t.is_active""")

    # Do not keep generated timestamps on rows that are only placeholders.
    con.execute("""UPDATE report_output SET generated_at=NULL, generated_by=NULL
        WHERE status<>'已生成'""")
    con.commit()

    print("report templates", con.execute("SELECT COUNT(*) FROM report_template").fetchone()[0],
          "categories", con.execute("SELECT COUNT(*) FROM report_category").fetchone()[0],
          "outputs", con.execute("SELECT COUNT(*) FROM report_output").fetchone()[0])
    for row in con.execute("""SELECT t.id,t.code,t.version,t.project,COUNT(o.id) c
        FROM report_template t LEFT JOIN report_output o ON o.template_id=t.id
        GROUP BY t.id ORDER BY t.id"""):
        print(dict(row))
    con.close()


if __name__ == "__main__":
    main()
