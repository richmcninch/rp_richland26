import re

with open('rp_richland26.vmf', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()

pos = text.find('"power" "4"')
start = text.rfind('dispinfo', 0, pos)
bstart = text.index('{', start)
depth = 1
i = bstart + 1
while depth:
    if text[i] == '{': depth += 1
    elif text[i] == '}': depth -= 1
    i += 1
block = text[bstart:i]

tt = block.find('triangle_tags')
tt_bstart = block.index('{', tt)
tt_bend = block.index('}', tt_bstart)
tt_content = block[tt_bstart:tt_bend+1]
rows = re.findall(r'"row(\d+)"\s+"([^"]+)"', tt_content)
print(f"triangle_tags rows: {len(rows)}")
if rows:
    print(f"  first row id: {rows[0][0]}, vals: {len(rows[0][1].split())}")
    print(f"  last  row id: {rows[-1][0]}, vals: {len(rows[-1][1].split())}")
    print(f"  sample: {rows[0][1][:80]}")
