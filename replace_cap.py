import re

with open('i:/back test vn/web_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

cap_worker_new = """def run_market_cap_worker(date: str):
    from datetime import datetime, timedelta
    try:
        dt_obj = datetime.strptime(date, '%Y-%m-%d')
        start_dt_str = (dt_obj - timedelta(days=15)).strftime('%Y-%m-%d')
        df_vn = state.engine.get_history('VNINDEX', start=start_dt_str, end=date)
        if not df_vn.empty:
            date = df_vn['time'].dt.strftime('%Y-%m-%d').max()
    except Exception as e:
        print(f"Error finding nearest date: {e}")

    with state.cap_lock:
        state.cap_state["running"] = True
        state.cap_state["progress"] = 0.0
        state.cap_state["current"] = 0
        state.cap_state["total"] = len(VN302)
        state.cap_state["results"] = []
        state.cap_state["industries_summary"] = []
        state.cap_state["top_10"] = []
        state.cap_state["error"] = None
        state.cap_state["date"] = date

    shares_map = {}
    try:
        conn = sqlite3.connect("market_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, outstanding_shares FROM ticker_shares")
        for row in cursor.fetchall():
            shares_map[row[0]] = row[1]
        conn.close()
    except Exception as e:
        print(f"Error loading ticker_shares: {e}")

    for sym, sh in FALLBACK_SHARES.items():
        if sym not in shares_map:
            shares_map[sym] = sh

    q = queue.Queue()
    for symbol in VN302:
        q.put(symbol)

    completed = 0
    progress_lock = threading.Lock()

    def prefetch_worker():
        nonlocal completed
        while state.cap_state["running"] and not q.empty():
            try:
                sym = q.get_nowait()
            except queue.Empty:
                break
            try:
                state.engine.get_history(sym, start=start_dt_str, end=date)
            except:
                pass
            finally:
                q.task_done()
                with progress_lock:
                    completed += 1
                    state.cap_state["current"] = completed
                    state.cap_state["progress"] = (completed / len(VN302)) * 90

    threads = []
    for _ in range(8):
        t = threading.Thread(target=prefetch_worker)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    results_list = []
    try:
        conn = sqlite3.connect("market_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, close FROM historical_prices WHERE time = ?", (date,))
        rows = cursor.fetchall()
        conn.close()
        
        price_map = {r[0]: r[1] for r in rows}
        
        for symbol in VN302:
            close_val = price_map.get(symbol, 0.0)
            shares = shares_map.get(symbol, 0)
            if shares == 0:
                shares = 100_000_000
                
            if close_val > 0:
                actual_price = close_val if close_val > 1000 else close_val * 1000
                market_cap_vnd = actual_price * shares
                market_cap_billion = round(market_cap_vnd / 1_000_000_000, 2)
                
                industry = "Chưa phân loại"
                for ind, symbols in VN302_INDUSTRIES.items():
                    if symbol in symbols:
                        industry = ind
                        break
                        
                results_list.append({
                    "Ticker": symbol,
                    "Industry": industry,
                    "Close": actual_price,
                    "OutstandingShares": shares,
                    "MarketCapBillion": market_cap_billion
                })
    except Exception as e:
        print(f"Error fetching aggregated cap: {e}")

    if results_list and state.cap_state["running"]:
        results_list = sorted(results_list, key=lambda x: x["MarketCapBillion"], reverse=True)
        
        for rank, r in enumerate(results_list, 1):
            r["Rank"] = rank
            
        top_10 = results_list[:10]
        
        industry_data = {}
        for r in results_list:
            ind = r["Industry"]
            if ind not in industry_data:
                industry_data[ind] = {"total_cap": 0.0, "count": 0}
            industry_data[ind]["total_cap"] += r["MarketCapBillion"]
            industry_data[ind]["count"] += 1
            
        industry_summary = []
        for ind, data in industry_data.items():
            industry_summary.append({
                "Industry": ind,
                "TotalCapBillion": round(data["total_cap"], 2),
                "Count": data["count"]
            })
        industry_summary = sorted(industry_summary, key=lambda x: x["TotalCapBillion"], reverse=True)
        
        with state.cap_lock:
            state.cap_state["results"] = results_list
            state.cap_state["top_10"] = top_10
            state.cap_state["industries_summary"] = industry_summary
            
    with state.cap_lock:
        state.cap_state["progress"] = 100.0
        state.cap_state["running"] = False"""

content = re.sub(r'def run_market_cap_worker\(date: str\):.*?state\.cap_state\["running"\] = False', cap_worker_new, content, flags=re.DOTALL)

with open('i:/back test vn/web_server.py', 'w', encoding='utf-8') as f:
    f.write(content)
