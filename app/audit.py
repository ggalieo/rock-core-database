# -*- coding: utf-8 -*-
"""Write audit entries for create/update/delete actions."""
import json
import time

from db_backend import is_postgres


def log(conn, actor, action, target, details=None):
    if isinstance(actor, dict):
        name = actor.get("account") or actor.get("name") or "system"
    else:
        name = str(actor or "system")
    payload = json.dumps(details or {}, ensure_ascii=False)
    if is_postgres():
        conn.execute("""INSERT INTO audit(user_name, action, target, details, created_at)
            VALUES (?,?,?,?::jsonb,?)""",
            (name, action, target, payload, time.strftime("%Y-%m-%d %H:%M:%S")))
    else:
        conn.execute("""INSERT INTO audit(user, action, target, details, created_at)
            VALUES (?,?,?,?,?)""",
            (name, action, target, payload, time.strftime("%Y-%m-%d %H:%M:%S")))
