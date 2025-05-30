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

    def create_tables(self):
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS members (
                discord_id BIGINT PRIMARY KEY,
                member_name TEXT NOT NULL
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                ticker TEXT PRIMARY KEY
            )
        ''')
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS members_requests (
                discord_id BIGINT,
                ticker TEXT,
                PRIMARY KEY (discord_id, ticker),
                FOREIGN KEY (discord_id) REFERENCES members(discord_id) ON DELETE CASCADE,
                FOREIGN KEY (ticker) REFERENCES requests(ticker) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()

    def _add_member(self, discord_id, member_name):
        self.cur.execute("""
            INSERT INTO members (discord_id, member_name)
            VALUES (%s, %s)
            ON CONFLICT (discord_id) DO NOTHING
        """, (discord_id, member_name))
        self.conn.commit()

    def _add_requests(self, tickers):
        for ticker in tickers:
            self.cur.execute("""
                INSERT INTO requests (ticker)
                VALUES (%s)
                ON CONFLICT DO NOTHING
            """, (ticker.upper(),))
        self.conn.commit()

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
