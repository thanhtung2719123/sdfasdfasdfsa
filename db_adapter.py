import os
import sqlite3
from urllib.parse import urlparse


def normalize_database_url(url: str) -> str:
    if not url:
        return url

    cleaned = url.strip().strip("\"'")
    if ";" in cleaned:
        cleaned = cleaned.split(";", 1)[0].strip()
    if cleaned.startswith("DATABASE_URL="):
        cleaned = cleaned.split("=", 1)[1].strip()
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://"):]

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"postgresql", "postgres"} or not parsed.hostname or not parsed.path.strip("/"):
        raise RuntimeError(
            "DATABASE_URL is invalid. Set it to one Postgres URL only, for example: "
            "postgresql://user:password@host:5432/database"
        )
    return cleaned


def uses_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def connect_database(sqlite_path: str = "market_cache.db"):
    database_url = normalize_database_url(os.getenv("DATABASE_URL"))
    if database_url:
        import psycopg

        if "sslmode=" not in database_url and "render.com" in database_url:
            separator = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{separator}sslmode=require"
        return PostgresConnection(psycopg.connect(database_url))

    conn = sqlite3.connect(sqlite_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn


class PostgresConnection:
    dialect = "postgres"

    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return PostgresCursor(self.conn.cursor())

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("PRAGMA"):
            return None
        cur = self.cursor()
        return cur.execute(sql, params)

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()

    def close(self):
        return self.conn.close()


class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def description(self):
        return self.cursor.description

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def execute(self, sql, params=None):
        sql = translate_sql(sql)
        return self.cursor.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        sql = translate_sql(sql)
        return self.cursor.executemany(sql, seq_of_params)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchmany(self, size=None):
        return self.cursor.fetchmany(size)

    def close(self):
        return self.cursor.close()


def translate_sql(sql: str) -> str:
    stripped = " ".join(sql.strip().split())
    upper = stripped.upper()

    if upper.startswith("PRAGMA"):
        return "SELECT 1"

    if upper.startswith("INSERT OR REPLACE INTO HISTORICAL_PRICES"):
        sql = sql.replace("INSERT OR REPLACE INTO", "INSERT INTO", 1)
        sql += """
            ON CONFLICT (symbol, time) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """
    elif upper.startswith("INSERT OR REPLACE INTO DAILY_LIQUIDITY"):
        sql = sql.replace("INSERT OR REPLACE INTO", "INSERT INTO", 1)
        sql += """
            ON CONFLICT (date, symbol) DO UPDATE SET
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                liquidity_vnd = EXCLUDED.liquidity_vnd,
                industry = EXCLUDED.industry
        """
    elif upper.startswith("INSERT OR REPLACE INTO DAILY_PRICE_RETURN"):
        sql = sql.replace("INSERT OR REPLACE INTO", "INSERT INTO", 1)
        sql += """
            ON CONFLICT (date, symbol) DO UPDATE SET
                industry = EXCLUDED.industry,
                close_vnd = EXCLUDED.close_vnd,
                return_pct = EXCLUDED.return_pct
        """
    elif upper.startswith("INSERT OR REPLACE INTO TICKER_SHARES"):
        sql = sql.replace("INSERT OR REPLACE INTO", "INSERT INTO", 1)
        sql += """
            ON CONFLICT (symbol) DO UPDATE SET
                outstanding_shares = EXCLUDED.outstanding_shares
        """
    elif upper.startswith("INSERT OR IGNORE INTO TICKER_SHARES"):
        sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1)
        sql += " ON CONFLICT (symbol) DO NOTHING"

    return sql.replace("?", "%s")
