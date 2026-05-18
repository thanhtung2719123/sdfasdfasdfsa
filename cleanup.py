with open('i:/back test vn/web_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def get_line_index(lines, start, string_to_match):
    for i in range(start, len(lines)):
        if string_to_match in lines[i]:
            return i
    return -1

# Clean up liq
liq_start = get_line_index(lines, 0, 'def run_liq_worker')
liq_end = get_line_index(lines, liq_start, 'state.liq_state["running"] = False')
crawler_start = get_line_index(lines, liq_end, 'def background_liquidity_crawler')
if crawler_start > liq_end + 2:
    del lines[liq_end + 1 : crawler_start - 1]

# Clean up cap
cap_start = get_line_index(lines, 0, 'def run_market_cap_worker')
cap_end = get_line_index(lines, cap_start, 'state.cap_state["running"] = False')
cap_route_start = get_line_index(lines, cap_end, '@app.post("/api/market-cap/start")')
if cap_route_start > cap_end + 2:
    del lines[cap_end + 1 : cap_route_start - 1]

# Clean up cap range
cap_range_start = get_line_index(lines, 0, 'def run_market_cap_range_worker')
cap_range_end = get_line_index(lines, cap_range_start, 'state.cap_range_state["progress"] = 100.0')
cap_range_route_start = get_line_index(lines, cap_range_end, '@app.post("/api/market-cap-range/start")')
if cap_range_route_start > cap_range_end + 3:  # +3 because there is a finally block
    # Let's find the end of the finally block which should be cap_range_end + 1 or +2.
    pass

with open('i:/back test vn/web_server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
