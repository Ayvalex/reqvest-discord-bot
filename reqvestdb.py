import sqlite3
from datetime import datetime

DB_FILE = "suggestions.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS members (
                member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_name TEXT NOT NULL UNIQUE
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL UNIQUE
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS members_suggestions (
                member_id INTEGER,
                suggestion_id INTEGER,
                PRIMARY KEY (member_id, suggestion_id),
                FOREIGN KEY (member_id) REFERENCES members(member_id),
                FOREIGN KEY (suggestion_id) REFERENCES suggestions(suggestion_id)
            )
        ''')

        conn.commit()

def get_member_id(conn, member_name):
    c = conn.cursor()
    c.execute('SELECT member_id FROM members WHERE member_name = ?', (member_name,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute('INSERT INTO members (member_name) VALUES (?)', (member_name,))
    return c.lastrowid

def get_suggestion_id(conn, stock_symbol):
    c = conn.cursor()
    c.execute('SELECT suggestion_id FROM suggestions WHERE stock_symbol = ?', (stock_symbol,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute('INSERT INTO suggestions (stock_symbol) VALUES (?)', (stock_symbol,))
    return c.lastrowid

def get_current_week():
    today = datetime.now()
    return today.strftime('%Y-%W') 

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
