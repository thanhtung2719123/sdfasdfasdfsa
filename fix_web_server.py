import ast

def get_var_from_file(file, varname):
    with open(file, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == varname:
                    return node.value.value
    return ''

liq = get_var_from_file('i:/back test vn/replace_liq.py', 'liq_worker_new')
cap = get_var_from_file('i:/back test vn/replace_cap.py', 'cap_worker_new')
cap_range = get_var_from_file('i:/back test vn/replace_cap_range.py', 'cap_range_worker_new')

with open('i:/back test vn/web_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def get_line_index(lines, start, prefixes):
    for i in range(start, len(lines)):
        for p in prefixes:
            if lines[i].startswith(p):
                return i
    return -1

def replace_block(lines, start_prefix, end_prefixes, new_text):
    start_idx = get_line_index(lines, 0, [start_prefix])
    if start_idx == -1: return lines
    end_idx = get_line_index(lines, start_idx + 1, end_prefixes)
    if end_idx == -1: return lines
    
    # insert new_text lines
    new_lines = [l + '\n' for l in new_text.strip().split('\n')]
    
    return lines[:start_idx] + new_lines + ['\n'] + lines[end_idx:]

lines = replace_block(lines, 'def run_liq_worker', ['# Background historical daemon crawler'], liq)
lines = replace_block(lines, 'def run_market_cap_worker', ['@app.post("/api/market-cap/start")'], cap)
lines = replace_block(lines, 'def run_market_cap_range_worker', ['@app.post("/api/market-cap-range/start")'], cap_range)

with open('i:/back test vn/web_server.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
