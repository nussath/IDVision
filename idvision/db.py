import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from passlib.context import CryptContext

from . import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

CRIMINAL_FIELDS = {"name", "age", "gender", "crime_details", "image_path", "status"}
MISSING_FIELDS = {"name", "age", "gender", "last_seen", "image_path", "status"}


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _conn():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


def _row(cur):
    r = cur.fetchone()
    return dict(r) if r else None


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS criminals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            crime_details TEXT,
            image_path TEXT,
            status TEXT DEFAULT 'wanted'
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS missing_persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            last_seen TEXT,
            image_path TEXT,
            status TEXT DEFAULT 'missing'
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL,
            category TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """)

        cur.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
        if cur.fetchone() is None:
            if config.INITIAL_ADMIN_USERNAME and config.INITIAL_ADMIN_PASSWORD:
                cur.execute(
                    "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                    (
                        config.INITIAL_ADMIN_USERNAME,
                        hash_password(config.INITIAL_ADMIN_PASSWORD),
                        "admin",
                    ),
                )
                print(
                    f"[init_db] Bootstrapped admin user '{config.INITIAL_ADMIN_USERNAME}' from environment."
                )
            else:
                print(
                    "[init_db] WARNING: no admin user exists. "
                    "Set INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD in .env "
                    "and restart, or register an admin via /register."
                )


# ---------- Users ----------

def register_user(username, password, role="viewer"):
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                (username, hash_password(password), role),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(username, password):
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        user = _row(cur)
    if user and verify_password(password, user["hashed_password"]):
        return user
    return None


def get_user(username):
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username=?", (username,))
        return _row(cur)


def list_users():
    with _conn() as conn:
        cur = conn.execute("SELECT id, username, role FROM users ORDER BY id")
        return _rows(cur)


def set_user_role(user_id, role):
    with _conn() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        return cur.rowcount > 0


def delete_user(user_id):
    with _conn() as conn:
        cur = conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        return cur.rowcount > 0


def has_any_admin():
    with _conn() as conn:
        cur = conn.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1")
        return cur.fetchone() is not None


# ---------- Criminals ----------

def add_criminal(name, age, gender, crime_details, image_path=""):
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO criminals (name, age, gender, crime_details, image_path)
               VALUES (?, ?, ?, ?, ?)""",
            (name, age, gender, crime_details, image_path),
        )
        return cur.lastrowid


def get_criminals():
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM criminals ORDER BY id DESC")
        return _rows(cur)


def get_criminal(criminal_id):
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM criminals WHERE id=?", (criminal_id,))
        return _row(cur)


def update_criminal(criminal_id, **fields):
    fields = {k: v for k, v in fields.items() if k in CRIMINAL_FIELDS}
    if not fields:
        return False
    assignments = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [criminal_id]
    with _conn() as conn:
        cur = conn.execute(f"UPDATE criminals SET {assignments} WHERE id=?", values)
        return cur.rowcount > 0


def delete_criminal(criminal_id):
    with _conn() as conn:
        cur = conn.execute("DELETE FROM criminals WHERE id=?", (criminal_id,))
        return cur.rowcount > 0


# ---------- Missing persons ----------

def add_missing_person(name, age, gender, last_seen, image_path=""):
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO missing_persons (name, age, gender, last_seen, image_path)
               VALUES (?, ?, ?, ?, ?)""",
            (name, age, gender, last_seen, image_path),
        )
        return cur.lastrowid


def get_missing_persons():
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM missing_persons ORDER BY id DESC")
        return _rows(cur)


def get_missing_person(person_id):
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM missing_persons WHERE id=?", (person_id,))
        return _row(cur)


def update_missing_person(person_id, **fields):
    fields = {k: v for k, v in fields.items() if k in MISSING_FIELDS}
    if not fields:
        return False
    assignments = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [person_id]
    with _conn() as conn:
        cur = conn.execute(f"UPDATE missing_persons SET {assignments} WHERE id=?", values)
        return cur.rowcount > 0


def delete_missing_person(person_id):
    with _conn() as conn:
        cur = conn.execute("DELETE FROM missing_persons WHERE id=?", (person_id,))
        return cur.rowcount > 0


# ---------- Alerts ----------

def add_alert(person_name, category, timestamp=None):
    ts = timestamp or _now_iso()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO alerts (person_name, category, timestamp) VALUES (?, ?, ?)",
            (person_name, category, ts),
        )
        return cur.lastrowid


def get_alerts():
    with _conn() as conn:
        cur = conn.execute("SELECT * FROM alerts ORDER BY id DESC")
        return _rows(cur)


def get_recent_alerts(limit=20):
    with _conn() as conn:
        cur = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (int(limit),)
        )
        return _rows(cur)


def delete_alert(alert_id):
    with _conn() as conn:
        cur = conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
        return cur.rowcount > 0


def clear_alerts():
    with _conn() as conn:
        conn.execute("DELETE FROM alerts")
