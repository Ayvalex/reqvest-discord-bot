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
                guild_id BIGINT,
                discord_id BIGINT,
                member_name TEXT NOT NULL,
                PRIMARY KEY (guild_id, discord_id)
            )
        ''')

        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                guild_id BIGINT,
                ticker TEXT,
                PRIMARY KEY (guild_id, ticker)
            )
        ''')

        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS members_requests (
                guild_id BIGINT,
                discord_id BIGINT,
                ticker TEXT,
                PRIMARY KEY (guild_id, discord_id, ticker),
                FOREIGN KEY (guild_id, discord_id) REFERENCES members(guild_id, discord_id) ON DELETE CASCADE,
                FOREIGN KEY (guild_id, ticker) REFERENCES requests(guild_id, ticker) ON DELETE CASCADE
            )
        ''')

        self.conn.commit()

    def _add_member(self, guild_id, discord_id, member_name):
        self.cur.execute("""
            INSERT INTO members (guild_id, discord_id, member_name)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (guild_id, discord_id, member_name))
        self.conn.commit()

    def _add_requests(self, guild_id, tickers):
        for ticker in tickers:
            self.cur.execute("""
                INSERT INTO requests (guild_id, ticker)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (guild_id, ticker.upper()))
        self.conn.commit()

    def _link_member_to_requests(self, guild_id, discord_id, tickers):
        for ticker in tickers:
            self.cur.execute("""
                INSERT INTO members_requests (guild_id, discord_id, ticker)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (guild_id, discord_id, ticker.upper()))
        self.conn.commit()

    def add_member_requests(self, guild_id, discord_id, tickers, member_name):
        self._add_member(guild_id, discord_id, member_name)
        self._add_requests(guild_id, tickers)
        self._link_member_to_requests(guild_id, discord_id, tickers)

    def requests_count(self, guild_id):
        self.cur.execute("""
            SELECT ticker, COUNT(*) as votes
            FROM members_requests
            WHERE guild_id = %s
            GROUP BY ticker
            ORDER BY votes DESC
        """, (guild_id,))
        return self.cur.fetchall()
    
    def reset_all_data(self, guild_id):
        self.cur.execute("""
            DELETE FROM members_requests WHERE guild_id = %s;
            DELETE FROM members WHERE guild_id = %s;
            DELETE FROM requests WHERE guild_id = %s;
        """, (guild_id, guild_id, guild_id))
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()

