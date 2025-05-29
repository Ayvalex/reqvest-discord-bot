import psycopg2

class Database:
    def __init__(self, host, database, user, password):
        self.conn = psycopg2.connect(
            host= host,        
            database=database,   
            user=user,          
            password=password   
        )
        self.cur = self.conn.cursor()

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

def add_suggestions(discord_id, stock_symbols, member_name="Unknown"):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        c.execute('''
            INSERT OR IGNORE INTO members (discord_id, member_name)
            VALUES (?, ?)
        ''', (discord_id, member_name))

        for symbol in stock_symbols:
            c.execute('''
                INSERT OR IGNORE INTO suggestions (stock_symbol)
                VALUES (?)
            ''', (symbol,))

            try:
                c.execute('''
                    INSERT INTO members_suggestions (discord_id, stock_symbol)
                    VALUES (?, ?)
                ''', (discord_id, symbol))
            except sqlite3.IntegrityError:
                pass  

        conn.commit()

def tally_suggestions():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.stock_symbol, COUNT(ms.discord_id) AS votes
            FROM suggestions s
            JOIN members_suggestions ms ON s.stock_symbol = ms.stock_symbol
            GROUP BY s.stock_symbol
            ORDER BY votes DESC
        ''')
        return c.fetchall()

def reset_suggestions():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM members_suggestions')
        c.execute('DELETE FROM suggestions')
        c.execute('DELETE FROM members')
        conn.commit()
