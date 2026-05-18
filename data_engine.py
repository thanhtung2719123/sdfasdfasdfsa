import os
import sqlite3
try:
    import libsql
except ImportError:
    import sqlite3 as libsql
import threading
import time
import pandas as pd
from datetime import datetime, timedelta
from vnstock import Quote, Listing

class RateLimiter:
    def __init__(self, requests_per_minute=55):
        self.delay = 60.0 / requests_per_minute
        self.last_request_time = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self.last_request_time = time.time()

class DataEngine:
    def __init__(self, source='KBS', db_path='market_cache.db'):
        self.source = source
        self.listing = Listing(source=self.source)
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self.rate_limiter = RateLimiter(requests_per_minute=55)
        self._init_db()

    def _get_conn(self):
        db_url = os.getenv("TURSO_URL")
        db_token = os.getenv("TURSO_AUTH_TOKEN")
        
        if db_url and db_token:
            return libsql.connect(db_url, auth_token=db_token)

        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            pass
        return conn


    def _init_db(self):
        with self.db_lock:
            try:
                conn = self._get_conn()
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS historical_prices (
                        symbol TEXT,
                        time TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume INTEGER,
                        PRIMARY KEY (symbol, time)
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_time ON historical_prices (symbol, time)")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error initializing SQLite cache DB: {e}")

    def get_all_symbols(self):
        """Returns a list of all stock symbols."""
        try:
            df = self.listing.all_symbols()
            if 'symbol' in df.columns:
                return df['symbol'].tolist()
            elif not df.empty:
                # Fallback to first column if 'symbol' not found
                return df.iloc[:, 0].tolist()
            return []
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return []

    def _read_cache(self, symbol, start_date, end_date):
        with self.db_lock:
            try:
                conn = self._get_conn()
                query = """
                    SELECT * FROM historical_prices 
                    WHERE symbol = ? AND time >= ? AND time <= ?
                """
                df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))
                conn.close()
                if not df.empty:
                    df['time'] = pd.to_datetime(df['time'])
                return df
            except Exception as e:
                print(f"Error reading cache for {symbol}: {e}")
                return pd.DataFrame()

    def _write_cache(self, symbol, df):
        if df.empty:
            return
        
        insert_df = df.copy()
        insert_df['symbol'] = symbol
        insert_df['time'] = insert_df['time'].dt.strftime('%Y-%m-%d')
        
        columns = ['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']
        insert_df = insert_df[[c for c in columns if c in insert_df.columns]]
        
        with self.db_lock:
            try:
                conn = self._get_conn()
                cursor = conn.cursor()
                for _, row in insert_df.iterrows():
                    cursor.execute("""
                        INSERT OR REPLACE INTO historical_prices (symbol, time, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (row['symbol'], row['time'], row['open'], row['high'], row['low'], row['close'], int(row['volume'])))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error writing cache for {symbol}: {e}")

    def _fetch_from_api(self, symbol, interval='1D', start=None, end=None, length=None):
        """Fetches data from api directly."""
        self.rate_limiter.wait()
        try:
            quote = Quote(symbol=symbol, source=self.source)
            if length:
                df = quote.history(length=length, interval=interval)
            else:
                df = quote.history(start=start, end=end, interval=interval)
            
            # Auto-scale Indices
            indices = ['VNINDEX', 'VN30', 'HNXINDEX', 'HNX30', 'UPCOMINDEX']
            if symbol.upper() in indices and not df.empty:
                for col in ['open', 'high', 'low', 'close']:
                    if df[col].max() < 10:
                        df[col] = df[col] * 1000

            df['time'] = pd.to_datetime(df['time'])
            return df
        except Exception as e:
            print(f"Error fetching history from API for {symbol}: {e}")
            return pd.DataFrame()

    def get_history(self, symbol, interval='1D', start=None, end=None, length=None):
        """Fetches historical price data with SQLite caching."""
        if interval != '1D':
            return self._fetch_from_api(symbol, interval, start, end, length)

        symbol = symbol.upper()
        today_str = datetime.today().strftime('%Y-%m-%d')
        
        # Handle case where length is specified instead of start date
        if length:
            # We want length rows. Query cache first.
            cached_all = self._read_cache(symbol, '2024-01-01', today_str)
            if not cached_all.empty and len(cached_all) >= length:
                latest_cached_date = cached_all['time'].max().strftime('%Y-%m-%d')
                if latest_cached_date < today_str:
                    next_day = (pd.to_datetime(latest_cached_date) + timedelta(days=1)).strftime('%Y-%m-%d')
                    api_df = self._fetch_from_api(symbol, interval, start=next_day, end=today_str)
                    if not api_df.empty:
                        self._write_cache(symbol, api_df)
                        combined = pd.concat([cached_all, api_df]).drop_duplicates(subset=['time'])
                        combined = combined.sort_values('time').reset_index(drop=True)
                        return combined.tail(length)
                return cached_all.tail(length)
            else:
                # Cache missed or not enough length, fetch a larger set (from 2024) to fill the cache
                api_df = self._fetch_from_api(symbol, interval, start='2024-01-01', end=today_str)
                if not api_df.empty:
                    self._write_cache(symbol, api_df)
                    return api_df.tail(length)
                return pd.DataFrame()

        # Regular date-based queries
        q_start = start if start else '2024-01-01'
        q_end = end if end else today_str
        
        cached_df = self._read_cache(symbol, q_start, q_end)
        
        if not cached_df.empty:
            fetched_parts = []
            earliest_cached_date = cached_df['time'].min().strftime('%Y-%m-%d')
            latest_cached_date = cached_df['time'].max().strftime('%Y-%m-%d')

            # Fill missing history before the first cached row. This is required
            # when the first sync was interrupted or the API only cached a short
            # recent window.
            if earliest_cached_date > q_start:
                prev_day = (pd.to_datetime(earliest_cached_date) - timedelta(days=1)).strftime('%Y-%m-%d')
                api_df = self._fetch_from_api(symbol, interval, start=q_start, end=prev_day)
                if not api_df.empty:
                    self._write_cache(symbol, api_df)
                    fetched_parts.append(api_df)
            
            if latest_cached_date < q_end:
                next_day = (pd.to_datetime(latest_cached_date) + timedelta(days=1)).strftime('%Y-%m-%d')
                api_df = self._fetch_from_api(symbol, interval, start=next_day, end=q_end)
                if not api_df.empty:
                    self._write_cache(symbol, api_df)
                    fetched_parts.append(api_df)

            if fetched_parts:
                combined = pd.concat([cached_df] + fetched_parts).drop_duplicates(subset=['time'])
                return combined.sort_values('time').reset_index(drop=True)
            
            return cached_df.sort_values('time').reset_index(drop=True)

        api_df = self._fetch_from_api(symbol, interval, start=q_start, end=q_end)
        if not api_df.empty:
            self._write_cache(symbol, api_df)
        return api_df
