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

def get_current_week():
    today = datetime.now()
    return today.strftime('%Y-%W')  # Year-Week format

def add_suggestions(user_id, stock_symbols):
    week = get_current_week()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        for symbol in stock_symbols:
            c.execute('''
                SELECT 1 FROM suggestions
                WHERE user_id = ? AND stock_symbol = ? AND week_start = ?
            ''', (user_id, symbol, week))
            if not c.fetchone():
                c.execute('''
                    INSERT INTO suggestions (user_id, stock_symbol, week_start)
                    VALUES (?, ?, ?)
                ''', (user_id, symbol, week))
        conn.commit()

def tally_suggestions():
    week = get_current_week()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT stock_symbol, COUNT(DISTINCT user_id) as votes
            FROM suggestions
            WHERE week_start = ?
            GROUP BY stock_symbol
            ORDER BY votes DESC
        ''', (week,))
        return c.fetchall()

def reset_suggestions():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM suggestions')
        conn.commit()
