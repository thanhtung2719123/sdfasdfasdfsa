import re

with open('i:/back test vn/web_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

cap_range_worker_new = """def run_market_cap_range_worker(start_date: str, end_date: str):
    with state.cap_range_lock:
        state.cap_range_state["running"] = True
        state.cap_range_state["progress"] = 0.0
        state.cap_range_state["current"] = 0
        state.cap_range_state["total"] = 0
        state.cap_range_state["daily_summaries"] = []
        state.cap_range_state["details_by_date"] = {}
        state.cap_range_state["error"] = None
        state.cap_range_state["start_date"] = start_date
        state.cap_range_state["end_date"] = end_date

    try:
        df_bench = state.engine.get_history("VCB", start=start_date, end=end_date)
        if df_bench.empty:
            df_bench = state.engine.get_history("HPG", start=start_date, end=end_date)
            
        if df_bench.empty:
            conn = sqlite3.connect("market_cache.db")
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT time FROM historical_prices WHERE time >= ? AND time <= ? ORDER BY time", (start_date, end_date))
            trading_days = [row[0] for row in cursor.fetchall()]
            conn.close()
        else:
            trading_days = sorted(df_bench['time'].dt.strftime('%Y-%m-%d').unique().tolist())

        if not trading_days:
            try:
                conn = sqlite3.connect("market_cache.db")
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT date FROM daily_liquidity WHERE date >= ? AND date <= ? ORDER BY date", (start_date, end_date))
                trading_days = [row[0] for row in cursor.fetchall()]
                conn.close()
            except:
                pass

        if not trading_days:
            raise Exception("Không tìm thấy ngày giao dịch nào trong khoảng thời gian đã chọn.")

        with state.cap_range_lock:
            state.cap_range_state["total"] = len(trading_days)

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

        # Batch pre-fetch missing symbols using multi-threaded parallel queue
        try:
            conn = sqlite3.connect("market_cache.db")
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM historical_prices WHERE time >= ? AND time <= ?", (start_date, end_date))
            cached_symbols = {row[0] for row in cursor.fetchall()}
            conn.close()
            
            missing_symbols = [s for s in VN302 if s not in cached_symbols]
            if missing_symbols:
                print(f"Range Scan Warmup: Pre-fetching {len(missing_symbols)} symbols directly to warm cache: {missing_symbols}")
                warmup_q = queue.Queue()
                for sym in missing_symbols:
                    warmup_q.put(sym)
                    
                def warmup_worker():
                    while not warmup_q.empty():
                        try:
                            s = warmup_q.get_nowait()
                        except queue.Empty:
                            break
                        try:
                            state.engine.get_history(s, start=start_date, end=end_date)
                        except Exception as e:
                            pass
                        finally:
                            warmup_q.task_done()
                            
                threads = []
                for _ in range(8):
                    t = threading.Thread(target=warmup_worker)
                    t.start()
                    threads.append(t)
                for t in threads:
                    t.join()
        except Exception as e:
            print(f"Error in range scan warmup: {e}")

        # In-memory aggregation
        conn = sqlite3.connect("market_cache.db")
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, time, open, high, low, close, volume FROM historical_prices WHERE time >= ? AND time <= ?", (start_date, end_date))
        all_price_rows = cursor.fetchall()
        conn.close()

        price_map_by_date = {}
        for r in all_price_rows:
            sym, t, o, h, l, c, v = r
            if t not in price_map_by_date:
                price_map_by_date[t] = {}
            price_map_by_date[t][sym] = {
                "open": o, "high": h, "low": l, "close": c, "volume": v
            }

        daily_summaries = []
        details_by_date = {}

        for idx, date in enumerate(trading_days, 1):
            if not state.cap_range_state["running"]:
                break

            price_map = price_map_by_date.get(date, {})
            results_list = []

            for symbol in VN302:
                item_data = price_map.get(symbol)
                
                open_val, high_val, low_val, close_val, volume_val = 0.0, 0.0, 0.0, 0.0, 0
                
                if item_data:
                    open_val = item_data["open"]
                    high_val = item_data["high"]
                    low_val = item_data["low"]
                    close_val = item_data["close"]
                    volume_val = item_data["volume"]

                shares = shares_map.get(symbol, 0)
                if shares == 0:
                    shares = 100_000_000

                if close_val > 0:
                    actual_price = close_val if close_val > 1000 else close_val * 1000
                    market_cap_billion = round((actual_price * shares) / 1_000_000_000, 2)
                    
                    liq_vnd = calculate_official_value(
                        symbol=symbol,
                        open_p=open_val if open_val > 0 else close_val,
                        high_p=high_val if high_val > 0 else close_val,
                        low_p=low_val if low_val > 0 else close_val,
                        close_p=close_val,
                        volume=volume_val
                    )
                    liq_billion = round(liq_vnd / 1_000_000_000, 4)

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
                        "MarketCapBillion": market_cap_billion,
                        "LiquidityBillion": liq_billion,
                        "Volume": volume_val
                    })

            if results_list:
                results_list = sorted(results_list, key=lambda x: x["MarketCapBillion"], reverse=True)
                for rank, r in enumerate(results_list, 1):
                    r["Rank"] = rank

                total_cap = sum(r["MarketCapBillion"] for r in results_list)
                total_liq = sum(r["LiquidityBillion"] for r in results_list)
                leader_r = results_list[0]
                
                liq_sorted = sorted(results_list, key=lambda x: x["LiquidityBillion"], reverse=True)
                liq_leader_r = liq_sorted[0]

                daily_summaries.append({
                    "Date": date,
                    "TotalCapBillion": round(total_cap, 2),
                    "LeaderTicker": leader_r["Ticker"],
                    "LeaderCapBillion": leader_r["MarketCapBillion"],
                    "TotalLiquidityBillion": round(total_liq, 2),
                    "LiquidityLeaderTicker": liq_leader_r["Ticker"],
                    "LiquidityLeaderBillion": round(liq_leader_r["LiquidityBillion"], 2),
                    "TickerCount": len(results_list)
                })
                
                details_by_date[date] = results_list

            with state.cap_range_lock:
                state.cap_range_state["current"] = idx
                state.cap_range_state["progress"] = (idx / len(trading_days)) * 100

        with state.cap_range_lock:
            state.cap_range_state["daily_summaries"] = daily_summaries
            state.cap_range_state["details_by_date"] = details_by_date

    except Exception as e:
        with state.cap_range_lock:
            state.cap_range_state["error"] = str(e)
            
    finally:
        with state.cap_range_lock:
            state.cap_range_state["running"] = False
            state.cap_range_state["progress"] = 100.0"""

content = re.sub(r'def run_market_cap_range_worker\(start_date: str, end_date: str\):.*?state\.cap_range_state\["progress"\] = 100\.0', cap_range_worker_new, content, flags=re.DOTALL)

with open('i:/back test vn/web_server.py', 'w', encoding='utf-8') as f:
    f.write(content)
