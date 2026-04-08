import re
log = open('rp_richland26.log', encoding='utf-8', errors='replace').read()
lines = log.split('\n')
last_start = max(i for i,l in enumerate(lines) if 'materialPath' in l)
section = '\n'.join(lines[last_start:])

mat = re.findall(r"Can.t find texture|material.*not found|LoadMaterial.*failed", section, re.IGNORECASE)
print(f'Material issues: {len(mat)}')

mod = [l for l in lines[last_start:] if 'error' in l.lower() and ('mdl' in l.lower() or 'model' in l.lower())]
print(f'Model issues: {len(mod)}')
for m in mod[:10]:
    print(' ', m)

print()
for l in lines[last_start:]:
    if 'skybox' in l.lower() or ('sky_' in l.lower() and 'warn' in l.lower()):
        print(l)
