# -*- coding: utf-8 -*-
"""Drop legacy tables after mainstream/report migration is complete."""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "core.db"


def main():
    if not DB_PATH.exists():
        return
    con = sqlite3.connect(DB_PATH)
    # children before parents
    for table in ("experiment_depth", "experiments", "core_observation",
                  "well_chart", "chart_template", "chart_category"):
        con.execute(f'DROP TABLE IF EXISTS "{table}"')
    con.commit()
    left = [r[0] for r in con.execute("""SELECT name FROM sqlite_master
        WHERE type='table' AND name IN
        ('experiment_depth','experiments','core_observation','well_chart','chart_template','chart_category')""")]
    print("legacy tables left:", left)
    con.close()


if __name__ == "__main__":
    main()
