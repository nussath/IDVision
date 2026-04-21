import sqlite3
from passlib.context import CryptContext

DB_NAME = "surveillance.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def init_db():
    conn = get_connection()
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

    cur.execute("SELECT * FROM users WHERE username=?", ("police",))
    user = cur.fetchone()

    if not user:
        cur.execute("""
        INSERT INTO users (username, hashed_password, role)
        VALUES (?, ?, ?)
        """, ("police", hash_password("1234"), "admin"))

    conn.commit()
    conn.close()

def register_user(username, password, role="viewer"):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO users (username, hashed_password, role)
        VALUES (?, ?, ?)
        """, (username, hash_password(password), role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    conn.close()

    if user and verify_password(password, user["hashed_password"]):
        return dict(user)
    return None

def add_criminal(name, age, gender, crime_details, image_path=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO criminals (name, age, gender, crime_details, image_path)
    VALUES (?, ?, ?, ?, ?)
    """, (name, age, gender, crime_details, image_path))
    conn.commit()
    conn.close()

def add_missing_person(name, age, gender, last_seen, image_path=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO missing_persons (name, age, gender, last_seen, image_path)
    VALUES (?, ?, ?, ?, ?)
    """, (name, age, gender, last_seen, image_path))
    conn.commit()
    conn.close()

def add_alert(person_name, category, timestamp):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO alerts (person_name, category, timestamp)
    VALUES (?, ?, ?)
    """, (person_name, category, timestamp))
    conn.commit()
    conn.close()

def get_criminals():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM criminals ORDER BY id DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_missing_persons():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM missing_persons ORDER BY id DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_alerts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts ORDER BY id DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows