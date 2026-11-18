# -*- coding: utf-8 -*-
"""Session login and role checks for the local demo server."""
import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie

SESSIONS = {}
SESSION_TTL = 8 * 3600
COOKIE = "core_session"
ITERATIONS = 120000


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password, stored):
    if not stored:
        return False
    try:
        algo, iterations, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)).hex()
        return hmac.compare_digest(calc, digest)
    except Exception:
        return False


def _role_key(row):
    if row.get("role_key"):
        return row["role_key"]
    role = str(row.get("role") or "")
    if "管理" in role:
        return "admin"
    if "审核" in role or "录入" in role or "数据" in role:
        return "editor"
    return "viewer"


def login(conn, account, password):
    row = conn.execute("SELECT * FROM users WHERE account=?", (account,)).fetchone()
    if not row:
        return None
    row = dict(row)
    if row.get("is_active") in (0, False):
        return None
    if not verify_password(password, row.get("password_hash")):
        return None
    user = {
        "id": row["id"], "account": row["account"], "name": row["name"],
        "role": row.get("role"), "role_key": _role_key(row),
    }
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {"user": user, "expires": time.time() + SESSION_TTL}
    conn.execute("UPDATE users SET last_login=? WHERE id=?",
                 (time.strftime("%Y-%m-%d %H:%M:%S"), row["id"]))
    conn.commit()
    return token, user


def logout(token):
    SESSIONS.pop(token, None)


def token_from_handler(handler):
    raw = handler.headers.get("Cookie", "")
    cookie = SimpleCookie()
    try:
        cookie.load(raw)
    except Exception:
        return None
    morsel = cookie.get(COOKIE)
    return morsel.value if morsel else None


def current_user(handler):
    token = token_from_handler(handler)
    if not token:
        return None
    sess = SESSIONS.get(token)
    if not sess:
        return None
    if sess["expires"] < time.time():
        SESSIONS.pop(token, None)
        return None
    return sess["user"]


def set_cookie(handler, token):
    handler.send_header("Set-Cookie", f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL}")


def clear_cookie(handler):
    handler.send_header("Set-Cookie", f"{COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
