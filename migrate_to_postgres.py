import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

SQLITE_DB = "market_cache.db"
# You can set this env variable or paste your connection string here
POSTGRES_URI = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/dbname")

def migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: Local database '{SQLITE_DB}' not found in the current directory.")
        return

    print("--- CONNECTING TO DATABASES ---")
    print(f"Reading from local SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    try:
        print(f"Connecting to Cloud PostgreSQL...")
        pg_conn = psycopg2.connect(POSTGRES_URI)
        pg_cursor = pg_conn.cursor()
        print("Successfully connected to cloud PostgreSQL!")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        print("Please check your DATABASE_URL environment variable or connection string.")
        sqlite_conn.close()
        return

    # 1. MIGRATE TICKER SHARES
    print("\n--- 1. MIGRATING TABLE: ticker_shares ---")
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticker_shares (
            symbol VARCHAR(20) PRIMARY KEY,
            outstanding_shares BIGINT
        )
    """)
    pg_conn.commit()

    sqlite_cursor.execute("SELECT symbol, outstanding_shares FROM ticker_shares")
    shares_data = sqlite_cursor.fetchall()
    print(f"Found {len(shares_data)} records in SQLite.")

    if shares_data:
        insert_shares_query = """
            INSERT INTO ticker_shares (symbol, outstanding_shares)
            VALUES %s
            ON CONFLICT (symbol) DO UPDATE SET outstanding_shares = EXCLUDED.outstanding_shares
        """
        execute_values(pg_cursor, insert_shares_query, shares_data)
        pg_conn.commit()
        print(f"Successfully migrated {len(shares_data)} records to PostgreSQL.")

    # 2. MIGRATE DAILY LIQUIDITY
    print("\n--- 2. MIGRATING TABLE: daily_liquidity ---")
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_liquidity (
            date VARCHAR(20),
            symbol VARCHAR(20),
            close DOUBLE PRECISION,
            volume BIGINT,
            liquidity_vnd BIGINT,
            industry VARCHAR(255),
            PRIMARY KEY (date, symbol)
        )
    """)
    pg_conn.commit()

    sqlite_cursor.execute("SELECT date, symbol, close, volume, liquidity_vnd, industry FROM daily_liquidity")
    liq_data = sqlite_cursor.fetchall()
    print(f"Found {len(liq_data)} records in SQLite.")

    if liq_data:
        insert_liq_query = """
            INSERT INTO daily_liquidity (date, symbol, close, volume, liquidity_vnd, industry)
            VALUES %s
            ON CONFLICT (date, symbol) DO UPDATE SET 
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                liquidity_vnd = EXCLUDED.liquidity_vnd,
                industry = EXCLUDED.industry
        """
        # Batch insert in chunks of 5000
        chunk_size = 5000
        total_records = len(liq_data)
        for i in range(0, total_records, chunk_size):
            chunk = liq_data[i:i + chunk_size]
            execute_values(pg_cursor, insert_liq_query, chunk)
            pg_conn.commit()
            print(f"Migrated {min(i + chunk_size, total_records)}/{total_records} daily_liquidity records...")
        print("Completed daily_liquidity migration!")

    # 3. MIGRATE HISTORICAL PRICES
    print("\n--- 3. MIGRATING TABLE: historical_prices ---")
    pg_cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_prices (
            symbol VARCHAR(20),
            time VARCHAR(20),
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            volume BIGINT,
            PRIMARY KEY (symbol, time)
        )
    """)
    pg_cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_time ON historical_prices (symbol, time)")
    pg_conn.commit()

    sqlite_cursor.execute("SELECT symbol, time, open, high, low, close, volume FROM historical_prices")
    
    # Process historical prices streaming (since it is a large table)
    insert_prices_query = """
        INSERT INTO historical_prices (symbol, time, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (symbol, time) DO UPDATE SET 
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    
    chunk_size = 5000
    chunk = []
    total_migrated = 0
    
    # Estimate total rows for logging
    sqlite_cursor_count = sqlite_conn.cursor()
    sqlite_cursor_count.execute("SELECT COUNT(*) FROM historical_prices")
    total_estimated = sqlite_cursor_count.fetchone()[0]
    print(f"Total historical_prices records to migrate: ~{total_estimated}")

    for row in sqlite_cursor:
        chunk.append(row)
        if len(chunk) >= chunk_size:
            execute_values(pg_cursor, insert_prices_query, chunk)
            pg_conn.commit()
            total_migrated += len(chunk)
            print(f"Migrated {total_migrated}/{total_estimated} historical_prices records...")
            chunk = []

    # Insert remaining records
    if chunk:
        execute_values(pg_cursor, insert_prices_query, chunk)
        pg_conn.commit()
        total_migrated += len(chunk)
        print(f"Migrated {total_migrated}/{total_estimated} historical_prices records...")

    print("Completed historical_prices migration!")

    print("\n--- MIGRATION COMPLETED SUCCESSFULLY ---")
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        POSTGRES_URI = sys.argv[1]
    
    if POSTGRES_URI == "postgresql://user:password@host:port/dbname":
        print("Error: Please provide a valid PostgreSQL connection string.")
        print("Usage: python migrate_to_postgres.py \"postgresql://username:password@hostname:5432/databasename\"")
        sys.exit(1)
        
    migrate()
