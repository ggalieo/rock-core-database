# -*- coding: utf-8 -*-
"""Separate report output artifacts from the core data layer.

Existing report_output rows were only placeholders/status flags.  After this
migration a generated row must point at a real file and carry renderer,
template and data version metadata.
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "core.db"


def main():
    if not DB_PATH.exists():
        return
    con = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in con.execute("PRAGMA table_info(report_output)")}
    add = {
        "source_type": "TEXT DEFAULT 'placeholder'",
        "renderer_key": "TEXT",
        "template_version": "TEXT",
        "data_version": "TEXT",
        "file_hash": "TEXT",
        "file_size": "INTEGER",
        "review_status": "TEXT DEFAULT '未审核'",
    }
    for name, decl in add.items():
        if name not in cols:
            con.execute(f"ALTER TABLE report_output ADD COLUMN {name} {decl}")

    con.execute("""UPDATE report_output SET
        template_version=(SELECT t.version FROM report_template t WHERE t.id=report_output.template_id)
        WHERE template_version IS NULL""")
    # No file means it is not a real generated result, regardless of old demo flags.
    con.execute("""UPDATE report_output SET status='未生成', generated_at=NULL,
        generated_by=NULL, source_type='placeholder'
        WHERE file_url IS NULL OR file_url=''""")
    con.commit()
    print("report_output", con.execute("SELECT COUNT(*) FROM report_output").fetchone()[0],
          "generated", con.execute("SELECT COUNT(*) FROM report_output WHERE status='已生成'").fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
