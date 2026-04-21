from database import init_db
import sqlite3
import os

db_path = "surveillance.db"

init_db()

print("DB exists:", os.path.exists(db_path))

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT id, username, role FROM users")
rows = cur.fetchall()

print("Users found:")
for row in rows:
    print(row)

conn.close()