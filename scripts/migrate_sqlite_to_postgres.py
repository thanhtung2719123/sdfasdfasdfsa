import argparse
import os
import sqlite3
from typing import Iterable, List, Sequence, Tuple

import psycopg


TABLES = {
    "historical_prices": {
        "create": """
            CREATE TABLE IF NOT EXISTS historical_prices (
                symbol TEXT NOT NULL,
                time TEXT NOT NULL,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume BIGINT,
                PRIMARY KEY (symbol, time)
            )
        """,
        "columns": ["symbol", "time", "open", "high", "low", "close", "volume"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_symbol_time ON historical_prices (symbol, time)",
            "CREATE INDEX IF NOT EXISTS idx_historical_prices_time ON historical_prices (time)",
        ],
    },
    "daily_liquidity": {
        "create": """
            CREATE TABLE IF NOT EXISTS daily_liquidity (
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                close DOUBLE PRECISION,
                volume BIGINT,
                liquidity_vnd BIGINT,
                industry TEXT,
                PRIMARY KEY (date, symbol)
            )
        """,
        "columns": ["date", "symbol", "close", "volume", "liquidity_vnd", "industry"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_daily_liquidity_date ON daily_liquidity (date)",
            "CREATE INDEX IF NOT EXISTS idx_daily_liquidity_symbol ON daily_liquidity (symbol)",
        ],
    },
    "daily_price_return": {
        "create": """
            CREATE TABLE IF NOT EXISTS daily_price_return (
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                industry TEXT,
                close_vnd DOUBLE PRECISION,
                return_pct DOUBLE PRECISION,
                PRIMARY KEY (date, symbol)
            )
        """,
        "columns": ["date", "symbol", "industry", "close_vnd", "return_pct"],
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_daily_price_return_date ON daily_price_return (date)",
            "CREATE INDEX IF NOT EXISTS idx_daily_price_return_symbol ON daily_price_return (symbol)",
        ],
    },
    "ticker_shares": {
        "create": """
            CREATE TABLE IF NOT EXISTS ticker_shares (
                symbol TEXT PRIMARY KEY,
                outstanding_shares BIGINT
            )
        """,
        "columns": ["symbol", "outstanding_shares"],
        "indexes": [],
    },
}


def batched(cursor: sqlite3.Cursor, size: int) -> Iterable[List[Tuple]]:
    while True:
        rows = cursor.fetchmany(size)
        if not rows:
            break
        yield rows


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def ensure_schema(pg_conn: psycopg.Connection) -> None:
    with pg_conn.cursor() as cur:
        for spec in TABLES.values():
            cur.execute(spec["create"])
            for index_sql in spec["indexes"]:
                cur.execute(index_sql)
    pg_conn.commit()


def table_exists(sqlite_conn: sqlite3.Connection, table: str) -> bool:
    cur = sqlite_conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg.Connection,
    table: str,
    columns: Sequence[str],
    batch_size: int,
    truncate: bool,
) -> int:
    if not table_exists(sqlite_conn, table):
        print(f"skip {table}: not found in SQLite")
        return 0

    if truncate:
        with pg_conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table}")
        pg_conn.commit()

    column_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    update_columns = [col for col in columns if col not in {"symbol", "time", "date"}]
    if table == "ticker_shares":
        conflict_key = "symbol"
        update_columns = ["outstanding_shares"]
    elif table == "historical_prices":
        conflict_key = "symbol, time"
    else:
        conflict_key = "date, symbol"

    update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_columns)
    insert_sql = f"""
        INSERT INTO {table} ({column_list})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_key}) DO UPDATE SET {update_clause}
    """

    sqlite_cur = sqlite_conn.execute(f"SELECT {column_list} FROM {table}")
    total = 0
    with pg_conn.cursor() as pg_cur:
        for rows in batched(sqlite_cur, batch_size):
            pg_cur.executemany(insert_sql, rows)
            total += len(rows)
            pg_conn.commit()
            print(f"{table}: migrated {total:,} rows")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate market_cache.db SQLite tables to PostgreSQL.")
    parser.add_argument("--sqlite", default="market_cache.db", help="Path to local SQLite DB.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="Postgres connection URL.")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--truncate", action="store_true", help="Clear destination tables before importing.")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Missing DATABASE_URL. Set it or pass --database-url.")
    if not os.path.exists(args.sqlite):
        raise SystemExit(f"SQLite file not found: {args.sqlite}")

    database_url = normalize_database_url(args.database_url)
    sqlite_conn = sqlite3.connect(args.sqlite)
    pg_conn = psycopg.connect(database_url)

    try:
        ensure_schema(pg_conn)
        total_rows = 0
        for table, spec in TABLES.items():
            total_rows += migrate_table(
                sqlite_conn=sqlite_conn,
                pg_conn=pg_conn,
                table=table,
                columns=spec["columns"],
                batch_size=args.batch_size,
                truncate=args.truncate,
            )
        print(f"Done. Migrated/updated {total_rows:,} rows.")
    finally:
        sqlite_conn.close()
        pg_conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
