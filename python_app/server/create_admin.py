#!/usr/bin/env python3
import sys
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / 'data' / 'app.sqlite3'

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: create_admin.py email password')
        sys.exit(1)
    email = sys.argv[1]
    password = sys.argv[2]
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        pw_hash = generate_password_hash(password)
        cur.execute('INSERT INTO users (email, password_hash, role, active) VALUES (?, ?, ?, ?)', (email, pw_hash, 'admin', 1))
        conn.commit()
        print('Admin user created:', email)
    except sqlite3.IntegrityError:
        print('User already exists')
    finally:
        conn.close()
