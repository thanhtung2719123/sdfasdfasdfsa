with open('i:/back test vn/web_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if l.startswith('def run_liq_worker'): print(f'liq worker starts at: {i}')
    if l.startswith('def run_market_cap_worker'): print(f'cap worker starts at: {i}')
    if l.startswith('def run_market_cap_range_worker'): print(f'cap range starts at: {i}')
    if l.startswith('@app.post("/api/liquidity/start")'): print(f'liq route at: {i}')
    if l.startswith('@app.post("/api/market-cap/start")'): print(f'cap route at: {i}')
    if l.startswith('@app.post("/api/market-cap-range/start")'): print(f'cap range route at: {i}')
    if l.startswith('def background_liquidity_crawler'): print(f'crawler at: {i}')
