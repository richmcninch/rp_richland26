import re

with open('rp_richland2026_restored.vmf', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

entities = re.findall(r'entity\s*\{(.*?)\n\}', content, re.DOTALL)
classnames = {}
for e in entities:
    m = re.search(r'"classname"\s+"([^"]+)"', e)
    if m:
        c = m.group(1)
        classnames[c] = classnames.get(c, 0) + 1

solids = content.count('solid\n{')
sky = re.search(r'"skyname"\s+"([^"]+)"', content)
print(f'Solids  : {solids}')
print(f'Entities: {len(entities)}')
print(f'Sky     : {sky.group(1) if sky else "NONE"}')
for k, v in sorted(classnames.items(), key=lambda x: -x[1]):
    print(f'  {v:5d}  {k}')
