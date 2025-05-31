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

    def _link_member_to_requests(self, discord_id, tickers):
        for ticker in tickers:
            self.cur.execute("""
                INSERT INTO members_requests (discord_id, ticker)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;""", (discord_id, ticker.upper()))
            
        self.conn.commit()

    def add_member_requests(self, discord_id, tickers, member_name):
        self._add_member(discord_id, member_name)
        self._add_requests(tickers)
        self._link_member_to_requests(discord_id, tickers)

    def requests_count(self):
        self.cur.execute("""
            SELECT ticker, COUNT(*) as votes
            FROM members_requests
            GROUP BY ticker
            ORDER BY votes DESC
        """)
        return self.cur.fetchall()

    def reset_all_data(self):
        self.cur.execute("TRUNCATE members, requests CASCADE")
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()
