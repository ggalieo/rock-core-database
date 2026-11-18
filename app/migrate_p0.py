# -*- coding: utf-8 -*-
"""P0 migration for SQLite: auth, audit details, soft delete and image metadata."""
import sqlite3
from pathlib import Path

from auth import hash_password

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "data" / "core.db"

SOFT_TABLES = [
    "wells", "runs", "sections", "core_observation", "core_fracture",
    "core_vug", "core_sidewall", "samples", "experiments", "coring_plan", "images",
]


def cols(con, table):
    return {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}


def add(con, table, name, decl):
    if name not in cols(con, table):
        con.execute(f'ALTER TABLE "{table}" ADD COLUMN {name} {decl}')


def main():
    if not DB_PATH.exists():
        print("DB not found", DB_PATH)
        return
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON")
    for t in SOFT_TABLES:
        add(con, t, "deleted_at", "TEXT")
    add(con, "users", "password_hash", "TEXT")
    add(con, "users", "role_key", "TEXT")
    add(con, "users", "is_active", "INTEGER DEFAULT 1")
    add(con, "audit", "details", "TEXT")
    add(con, "images", "object_key", "TEXT")
    add(con, "images", "thumb_key", "TEXT")
    add(con, "images", "content_type", "TEXT")
    add(con, "images", "size_bytes", "INTEGER")
    add(con, "images", "etag", "TEXT")

    for t in SOFT_TABLES:
        con.execute(f'CREATE INDEX IF NOT EXISTS idx_{t}_deleted ON "{t}"(deleted_at)')

    users = [
        ("admin", "admin123", "admin"),
        ("zhangwei", "editor123", "editor"),
        ("lina", "reviewer123", "editor"),
        ("wangqiang", "editor123", "editor"),
        ("chenjing", "viewer123", "viewer"),
    ]
    for account, password, role_key in users:
        row = con.execute("SELECT id FROM users WHERE account=?", (account,)).fetchone()
        if row:
            con.execute("UPDATE users SET password_hash=?, role_key=?, is_active=1 WHERE id=?",
                        (hash_password(password), role_key, row[0]))
        else:
            con.execute("""INSERT INTO users(name,account,role,org,role_key,password_hash,is_active)
                VALUES(?,?,?,?,?,?,1)""",
                (account, account, role_key, "演示", role_key, hash_password(password)))
    con.commit()
    con.close()
    print("P0 migration applied")


if __name__ == "__main__":
    main()
