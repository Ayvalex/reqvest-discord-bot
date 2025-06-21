import psycopg2
from psycopg2 import sql, OperationalError, DatabaseError

class Database:
    def __init__(self, host, database, user, password):
        self.connection_params = {
            "host": host,
            "database": database,
            "user": user,
            "password": password
        }

    def _get_connection(self):
        return psycopg2.connect(**self.connection_params)

    def create_tables(self):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS members (
                        guild_id BIGINT,
                        discord_id BIGINT,
                        member_name TEXT NOT NULL,
                        PRIMARY KEY (guild_id, discord_id)
                    )
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS requests (
                        guild_id BIGINT,
                        ticker TEXT,
                        PRIMARY KEY (guild_id, ticker)
                    )
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS members_requests (
                        guild_id BIGINT,
                        discord_id BIGINT,
                        ticker TEXT,
                        PRIMARY KEY (guild_id, discord_id, ticker),
                        FOREIGN KEY (guild_id, discord_id) REFERENCES members(guild_id, discord_id) ON DELETE CASCADE,
                        FOREIGN KEY (guild_id, ticker) REFERENCES requests(guild_id, ticker) ON DELETE CASCADE
                    )
                ''')

    def _add_member(self, conn, guild_id, discord_id, member_name):
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO members (guild_id, discord_id, member_name)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (guild_id, discord_id, member_name))

    def _add_requests(self, conn, guild_id, tickers):
        with conn.cursor() as cur:
            for ticker in tickers:
                cur.execute("""
                    INSERT INTO requests (guild_id, ticker)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (guild_id, ticker.upper()))

    def _link_member_to_requests(self, conn, guild_id, discord_id, tickers):
        with conn.cursor() as cur:
            for ticker in tickers:
                cur.execute("""
                    INSERT INTO members_requests (guild_id, discord_id, ticker)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (guild_id, discord_id, ticker.upper()))

    def add_member_requests(self, guild_id, discord_id, tickers, member_name):
        try:
            with self._get_connection() as conn:
                self._add_member(conn, guild_id, discord_id, member_name)
                self._add_requests(conn, guild_id, tickers)
                self._link_member_to_requests(conn, guild_id, discord_id, tickers)
        except (Exception, psycopg2.Error) as e:
            print(f"DB Error in add_member_requests: {e}")
            raise

    def requests_count(self, guild_id):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, COUNT(*) as votes
                    FROM members_requests
                    WHERE guild_id = %s
                    GROUP BY ticker
                    ORDER BY votes DESC
                """, (guild_id,))
                return cur.fetchall()

    def has_user_voted(self, guild_id, user_id):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM members_requests
                    WHERE guild_id = %s AND discord_id = %s
                    LIMIT 1
                """, (guild_id, user_id))
                return cur.fetchone() is not None

    def reset_all_data(self, guild_id):
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM members_requests WHERE guild_id = %s", (guild_id,))
                    cur.execute("DELETE FROM members WHERE guild_id = %s", (guild_id,))
                    cur.execute("DELETE FROM requests WHERE guild_id = %s", (guild_id,))
        except Exception as e:
            print(f"DB Error in reset_all_data: {e}")
            raise

    def close(self):
        pass
