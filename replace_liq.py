import re
with open('i:/back test vn/web_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

liq_worker_new = """def run_liq_worker(date: str):
    from datetime import datetime, timedelta
    try:
        dt_obj = datetime.strptime(date, '%Y-%m-%d')
        start_dt_str = (dt_obj - timedelta(days=15)).strftime('%Y-%m-%d')
        df_vn = state.engine.get_history('VNINDEX', start=start_dt_str, end=date)
        if not df_vn.empty:
            date = df_vn['time'].dt.strftime('%Y-%m-%d').max()
    except Exception as e:
        print(f"Error finding nearest date: {e}")

    with state.liq_lock:
        state.liq_state["running"] = True
        state.liq_state["progress"] = 0.0
        state.liq_state["current"] = 0
        state.liq_state["total"] = len(VN302)
        state.liq_state["results"] = []
        state.liq_state["summary"] = {}
        state.liq_state["error"] = None
        state.liq_state["date"] = date
        
    try:
        conn = sqlite3.connect("market_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_liquidity WHERE date = ?", (date,))
        count = cursor.fetchone()[0]
        
        if count >= len(VN302) - 20:
            cursor.execute(\"\"\"
                SELECT symbol, close, volume, liquidity_vnd, industry 
                FROM daily_liquidity 
                WHERE date = ? 
                ORDER BY liquidity_vnd DESC
            \"\"\", (date,))
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            total_value_vnd = 0
            total_volume = 0
            
            for r in rows:
                results.append({
                    "Ticker": r[0],
                    "Industry": r[4],
                    "Close": float(r[1]),
                    "Volume": int(r[2]),
                    "Liquidity_VND": int(r[3])
                })
                total_value_vnd += int(r[3])
                total_volume += int(r[2])
                
            leader_ticker = results[0]["Ticker"] if results else "N/A"
            avg_value_vnd = total_value_vnd / len(results) if results else 0
            
            summary = {
                "total_value_vnd": total_value_vnd,
                "total_volume": total_volume,
                "leader_ticker": leader_ticker,
                "avg_value_vnd": int(avg_value_vnd)
            }
            
            with state.liq_lock:
                state.liq_state["results"] = results
                state.liq_state["summary"] = summary
                state.liq_state["progress"] = 100.0
                state.liq_state["running"] = False
            print(f"Liquidity scan CACHE HIT for date {date} - loaded {len(results)} rows instantly.")
            return
        conn.close()
    except Exception as e:
        print(f"Error checking daily_liquidity cache: {e}")

    total = len(VN302)
    completed = 0
    progress_lock = threading.Lock()
    
    q = queue.Queue()
    for symbol in VN302:
        q.put(symbol)
        
    def worker():
        nonlocal completed
        while state.liq_state["running"]:
            try:
                symbol = q.get_nowait()
            except queue.Empty:
                break
            try:
                state.engine.get_history(symbol, start=start_dt_str, end=date)
            except Exception:
                pass
            finally:
                q.task_done()
                with progress_lock:
                    completed += 1
                    state.liq_state["current"] = completed
                    state.liq_state["progress"] = (completed / total) * 90

    threads = []
    for _ in range(8):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()
        
    results_list = []
    try:
        conn = sqlite3.connect("market_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, open, high, low, close, volume FROM historical_prices WHERE time = ?", (date,))
        rows = cursor.fetchall()
        conn.close()
        
        for r in rows:
            sym, o, h, l, c, v = r
            if sym in VN302 and v > 0:
                val_vnd = calculate_official_value(
                    symbol=sym, open_p=float(o), high_p=float(h),
                    low_p=float(l), close_p=float(c), volume=int(v)
                )
                industry = "Chưa phân loại"
                for ind, symbols in VN302_INDUSTRIES.items():
                    if sym in symbols:
                        industry = ind
                        break
                results_list.append({
                    "Ticker": sym,
                    "Industry": industry,
                    "Close": float(c) if c > 1000 else float(c * 1000),
                    "Volume": int(v),
                    "Liquidity_VND": val_vnd
                })
    except Exception as e:
        print(f"Error fetching aggregated liquidity: {e}")

    if results_list:
        results_list = sorted(results_list, key=lambda x: x["Liquidity_VND"], reverse=True)
        total_value_vnd = sum(item["Liquidity_VND"] for item in results_list)
        total_volume = sum(item["Volume"] for item in results_list)
        leader_ticker = results_list[0]["Ticker"] if results_list else "N/A"
        avg_value_vnd = total_value_vnd / len(results_list) if results_list else 0
        
        summary = {
            "total_value_vnd": total_value_vnd,
            "total_volume": total_volume,
            "leader_ticker": leader_ticker,
            "avg_value_vnd": int(avg_value_vnd)
        }
        
        try:
            conn = sqlite3.connect("market_cache.db")
            cursor = conn.cursor()
            for r in results_list:
                cursor.execute(\"\"\"
                    INSERT OR REPLACE INTO daily_liquidity (date, symbol, close, volume, liquidity_vnd, industry)
                    VALUES (?, ?, ?, ?, ?, ?)
                \"\"\", (date, r["Ticker"], r["Close"], r["Volume"], r["Liquidity_VND"], r["Industry"]))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error caching liquidity records: {e}")
            
        with state.liq_lock:
            state.liq_state["results"] = results_list
            state.liq_state["summary"] = summary
    else:
        with state.liq_lock:
            state.liq_state["results"] = []
            state.liq_state["summary"] = {"total_value_vnd": 0, "total_volume": 0, "leader_ticker": "N/A", "avg_value_vnd": 0}
            
    with state.liq_lock:
        state.liq_state["progress"] = 100.0
        state.liq_state["running"] = False
"""

content = re.sub(r'def run_liq_worker\(date: str\):.*?state\.liq_state\["running"\] = False', liq_worker_new, content, flags=re.DOTALL)

with open('i:/back test vn/web_server.py', 'w', encoding='utf-8') as f:
    f.write(content)
