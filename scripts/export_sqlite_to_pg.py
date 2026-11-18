# -*- coding: utf-8 -*-
"""Export the current SQLite demo DB to db/postgres/002_seed.sql."""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SQLITE = BASE / "app" / "data" / "core.db"
OUT = BASE / "db" / "postgres" / "002_seed.sql"


def lit(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return "'" + str(value).replace("'", "''") + "'"


def table_rows(conn, table, columns=None):
    cur = conn.execute(f'SELECT * FROM "{table}" ORDER BY 1')
    rows = [dict(r) for r in cur.fetchall()]
    if columns is None:
        columns = [d[0] for d in cur.description]
    return columns, rows


def insert_block(table, columns, rows, map_col=None):
    if not rows:
        return f"-- {table}: empty\n"
    cols = ", ".join(f'"{c}"' for c in columns)
    lines = []
    for r in rows:
        vals = []
        for c in columns:
            src = map_col.get(c, c) if map_col else c
            value = r.get(src)
            if (table == "users" and c == "is_active") or (table == "chart_template" and c == "is_active"):
                vals.append("TRUE" if value else "FALSE")
            else:
                vals.append(lit(value))
        lines.append(f"INSERT INTO {table} ({cols}) VALUES ({', '.join(vals)});")
    return "\n".join(lines) + "\n"


def main():
    conn = sqlite3.connect(SQLITE)
    conn.row_factory = sqlite3.Row
    out = []
    out.append("-- Generated from app/data/core.db; do not edit by hand.\n")
    out.append("SET client_encoding = 'UTF8';\nBEGIN;\n")
    out.append("""TRUNCATE TABLE
  well_chart, chart_template, chart_category, image_embedding, annotations, image_calibration, txns, inventory,
  experiment_depth, experiments, samples, core_sidewall, core_vug,
  core_fracture, core_observation, coring_plan, products, scans,
  image_depth, images, section_depth, sections, strata, run_depth,
  runs, well_geometry, wells, dictionary, users, audit, meta
RESTART IDENTITY CASCADE;
""")

    # simple tables first
    simple = [
        ("chart_category", None, None),
        ("chart_template", None, None),
        ("dictionary", None, None),
        ("wells", None, None),
        ("runs", None, None),
        ("strata", None, None),
        ("sections", None, None),
        ("images", None, None),
        ("scans", None, None),
        ("products", None, None),
        ("core_observation", None, None),
        ("core_fracture", None, None),
        ("core_vug", None, None),
        ("core_sidewall", None, None),
        ("samples", None, None),
        ("experiments", None, None),
        ("coring_plan", None, None),
        ("inventory", None, None),
        ("txns", None, None),
        ("annotations", None, None),
        ("image_calibration", None, None),
        ("users", None, None),
        ("meta", None, None),
        ("well_chart", None, None),
    ]

    for table, map_col, _ in simple:
        cols, rows = table_rows(conn, table)
        out.append(f"\n-- {table} ({len(rows)})\n")
        out.append(insert_block(table, cols, rows, map_col))

    # audit: SQLite uses "user"; PostgreSQL uses "user_name"
    _, audit_rows = table_rows(conn, "audit")
    out.append(f"\n-- audit ({len(audit_rows)})\n")
    out.append(insert_block(
        "audit",
        ["id", "user_name", "action", "target", "created_at"],
        audit_rows,
        {"user_name": "user"},
    ))

    out.append("""
-- object keys (MinIO / S3): core/<filename>
UPDATE images
SET object_key = 'core/' || split_part(file, '/', 3),
    thumb_key  = 'core/' || split_part(thumb, '/', 3)
WHERE file IS NOT NULL AND thumb IS NOT NULL;

UPDATE sections
SET strip_key = 'core/' || split_part(strip_file, '/', 3)
WHERE strip_file IS NOT NULL;

-- PostGIS point mirror
INSERT INTO well_geometry (well_id, geom)
SELECT id, ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
FROM wells
WHERE lon IS NOT NULL AND lat IS NOT NULL;

-- range mirrors
INSERT INTO run_depth (run_id, depth)
SELECT id, numrange(top_md, bottom_md, '[)')
FROM runs
WHERE top_md IS NOT NULL AND bottom_md IS NOT NULL AND top_md < bottom_md;

INSERT INTO section_depth (section_id, depth)
SELECT id, numrange(top_md, bottom_md, '[)')
FROM sections
WHERE top_md IS NOT NULL AND bottom_md IS NOT NULL AND top_md < bottom_md;

INSERT INTO image_depth (image_id, depth)
SELECT id, numrange(top_md, bottom_md, '[)')
FROM images
WHERE top_md IS NOT NULL AND bottom_md IS NOT NULL AND top_md < bottom_md;

INSERT INTO experiment_depth (experiment_id, depth)
SELECT id, numrange(top_md, bottom_md, '[)')
FROM experiments
WHERE top_md IS NOT NULL AND bottom_md IS NOT NULL AND top_md < bottom_md;
""")

    # sequences
    id_tables = ["chart_template", "well_chart", "wells", "runs", "strata", "sections", "images", "scans", "products",
                 "core_observation", "core_fracture", "core_vug", "core_sidewall",
                 "samples", "experiments", "coring_plan", "inventory", "txns",
                 "annotations", "image_calibration", "users", "audit"]
    for t in id_tables:
        out.append(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT max(id) FROM {t}), 1), true);\n")
    out.append("COMMIT;\n")
    OUT.write_text("".join(out), encoding="utf-8")
    print("wrote", OUT, "lines", len("".join(out).splitlines()), "size", OUT.stat().st_size)
    conn.close()


if __name__ == "__main__":
    main()
