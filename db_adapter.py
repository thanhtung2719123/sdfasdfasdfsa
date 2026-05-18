import os
import sqlite3

class PgCursorWrapper:
    def __init__(self, pg_cursor):
        self.cursor = pg_cursor

    def execute(self, sql, params=None):
        # 1. Translate parameter placeholder from SQLite '?' to PostgreSQL '%s'
        sql_pg = sql.replace('?', '%s')
        
        # 2. Dynamic Translation for SQLite-specific keywords to PostgreSQL CONFLICT syntax
        if "INSERT OR REPLACE INTO daily_liquidity" in sql:
            sql_pg = """
                INSERT INTO daily_liquidity (date, symbol, close, volume, liquidity_vnd, industry)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, symbol) DO UPDATE SET
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    liquidity_vnd = EXCLUDED.liquidity_vnd,
                    industry = EXCLUDED.industry
            """
        elif "INSERT OR REPLACE INTO ticker_shares" in sql:
            sql_pg = """
                INSERT INTO ticker_shares (symbol, outstanding_shares)
                VALUES (%s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    outstanding_shares = EXCLUDED.outstanding_shares
            """
        elif "INSERT OR IGNORE INTO ticker_shares" in sql:
            sql_pg = """
                INSERT INTO ticker_shares (symbol, outstanding_shares)
                VALUES (%s, %s)
                ON CONFLICT (symbol) DO NOTHING
            """
        elif "INSERT OR REPLACE INTO historical_prices" in sql:
            sql_pg = """
                INSERT INTO historical_prices (symbol, time, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, time) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            """
        
        # Execute psycopg2 query
        if params is not None:
            # PostgreSQL requires tuples or lists for parameters. Ensure proper formatting.
            self.cursor.execute(sql_pg, params)
        else:
            self.cursor.execute(sql_pg)

    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor)

    def __next__(self):
        return next(self.cursor)

    def __getattr__(self, name):
        return getattr(self.cursor, name)

class PgConnectionWrapper:
    def __init__(self, pg_conn):
        self.conn = pg_conn

    def cursor(self):
        return PgCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def execute(self, sql, params=None):
        # Silently bypass SQLite PRAGMA tuning commands in PostgreSQL
        if "PRAGMA" in sql:
            return None
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def __getattr__(self, name):
        return getattr(self.conn, name)

def get_db_conn(db_path='market_cache.db'):
    # Detect if we are in production/Vercel with Supabase
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        import psycopg2
        # Ensure connection string begins with standard 'postgresql://' for psycopg2 compatibility
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        pg_conn = psycopg2.connect(db_url)
        return PgConnectionWrapper(pg_conn)
    
    # On Vercel, force read-only mode for SQLite to prevent write locks on the read-only filesystem
    if os.getenv("VERCEL") == "1":
        return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30.0)

    # Otherwise, fallback transparently to local SQLite
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
