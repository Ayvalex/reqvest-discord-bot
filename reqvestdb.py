import sqlite3
from datetime import datetime

DB_FILE = "suggestions.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                stock_symbol TEXT,
                week_start DATE
            )
        ''')
        conn.commit()