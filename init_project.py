import os
import sqlite3

from idvision import config
from idvision.db import init_db

init_db()

print("DB exists:", os.path.exists(config.DB_PATH))

conn = sqlite3.connect(config.DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, username, role FROM users")

print("Users found:")
for row in cur.fetchall():
    print(row)

conn.close()
