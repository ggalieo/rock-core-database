# -*- coding: utf-8 -*-
"""Database adapter: SQLite demo by default, PostgreSQL 16 when DATABASE_URL is set."""
import os
import sqlite3


def is_postgres():
    return bool(os.environ.get("DATABASE_URL", "").strip())


class PgCursor:
    def __init__(self, cur):
        self._cur = cur

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(r) for r in self._cur.fetchall()]

    @property
    def rowcount(self):
        return self._cur.rowcount


class PgConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        # Existing API code uses sqlite-style "?" placeholders.
        return PgCursor(self._conn.execute(sql.replace("?", "%s"), params))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def connect(sqlite_path):
    if not is_postgres():
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as e:
        raise RuntimeError(
            "DATABASE_URL is set but psycopg is not installed. "
            "Run: pip install -r requirements-pg.txt"
        ) from e

    dsn = os.environ["DATABASE_URL"].strip()
    return PgConnection(psycopg.connect(dsn, row_factory=dict_row))
