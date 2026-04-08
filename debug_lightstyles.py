import re, math
from collections import defaultdict

vmf = open('rp_richland26.vmf', encoding='utf-8', errors='replace').read()
log = open('rp_richland26.log', encoding='utf-8', errors='replace').read()

# Get last vrad section only (find last 'materialPath' occurrence, which marks start of a vrad run)
lines = log.split('\n')
last_vrad_start = 0
for i, l in enumerate(lines):
    if 'materialPath' in l:
        last_vrad_start = i
vrad_log = '\n'.join(lines[last_vrad_start:])
print(f'Last vrad starts at log line {last_vrad_start} (of {len(lines)})')

warn_re = re.compile(r'Too many light styles on a face at \(([-0-9.]+),\s*([-0-9.]+),\s*([-0-9.]+)\)')
locs = [(float(x), float(y), float(z)) for x, y, z in warn_re.findall(vrad_log)]
print(f'Warning locs in last vrad: {len(locs)}')

# Parse named lights from VMF
ent_blk = re.compile(r'entity\s*\{(.*?)\n\}', re.DOTALL)
kv = re.compile(r'"(\w+)"\s+"([^"]+)"')
lights = []
for m in ent_blk.finditer(vmf):
    d = dict(kv.findall(m.group(1)))
    if d.get('classname') == 'light' and 'targetname' in d and 'origin' in d:
        ox, oy, oz = map(float, d['origin'].split())
        lights.append((d['targetname'], ox, oy, oz, float(d.get('_distance', '0'))))

print(f'Named lights: {len(lights)}')
print()

# For top warning locations, check which named lights are within their _distance
zone = defaultdict(set)
for wx, wy, wz in locs[:60]:
    for name, lx, ly, lz, dist in lights:
        d = math.sqrt((wx-lx)**2 + (wy-ly)**2 + (wz-lz)**2)
        if dist > 0 and d <= dist:
            zone[(wx,wy,wz)].add(name)
        elif dist == 0 and d <= 400:
            zone[(wx,wy,wz)].add(name)

print("Top zones by style count (within actual _distance):")
for loc, styles in sorted(zone.items(), key=lambda x: -len(x[1]))[:8]:
    print(f'  {loc}: {len(styles)} styles')
    for s in sorted(styles):
        print(f'    {s}')

# Also show unique light names contributing to any warning
all_contributors = set()
for styles in zone.values():
    all_contributors |= styles
print()
print(f"All contributing light names ({len(all_contributors)}):")
for n in sorted(all_contributors):
    print(f'  {n}')
