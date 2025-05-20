import sqlite3
from datetime import datetime

DB_FILE = "suggestions.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS members (
                discord_id INTEGER PRIMARY KEY,
                member_name TEXT NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                stock_symbol TEXT PRIMARY KEY
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS members_suggestions (
                discord_id INTEGER,
                stock_symbol TEXT,
                PRIMARY KEY (discord_id, stock_symbol),
                FOREIGN KEY (discord_id) REFERENCES members(discord_id),
                FOREIGN KEY (stock_symbol) REFERENCES suggestions(stock_symbol)
            )
        ''')

        conn.commit()

def add_suggestions(member_name, stock_symbols):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        member_id = get_member_id(conn, member_name)
        for symbol in stock_symbols:
            suggestion_id = get_suggestion_id(conn, symbol)
            try:
                c.execute('''
                    INSERT INTO members_suggestions (member_id, suggestion_id)
                    VALUES (?, ?)
                ''', (member_id, suggestion_id))
            except sqlite3.IntegrityError:
                pass  
        conn.commit()

def tally_suggestions():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.stock_symbol, COUNT(ms.member_id) AS votes
            FROM suggestions s
            JOIN members_suggestions ms ON s.suggestion_id = ms.suggestion_id
            GROUP BY s.stock_symbol
            ORDER BY votes DESC
        ''')
        return c.fetchall()

def reset_suggestions():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM members_suggestions')
        c.execute('DELETE FROM members')
        c.execute('DELETE FROM suggestions')
        conn.commit()
