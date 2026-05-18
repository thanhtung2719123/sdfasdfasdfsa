with open('web_server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'VN302_INDUSTRIES' in l or 'VN302 =' in l or 'import VN302' in l or 'DELISTED' in l:
        print(f'{i+1}: {l.strip()[:150]}')
