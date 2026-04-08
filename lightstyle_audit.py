"""
lightstyle_audit.py
For each "Too many light styles" face coordinate from the compile log,
find nearby light entities and show which have targetnames (=dynamic light styles).
"""
import re, math

VMF = "rp_richland26.vmf"

# Warning coords from the last compile log
WARN_COORDS = [
    (24.933, 858.5, 17),
    (-1352, 848.5, 17),
    (74.926, -47.963, 17),
    (-78.333, 61.667, 17),
    (-61.0, 41.32, 17),
    (-83.667, -60.333, 17),
    (-7.999, 792.0, 17),
    (-78.333, -59.667, 17),
    (1466, 942, 65),
    (1469.5, 875.75, 65),
    (-532, 302, 104),
    (1460, 1040, 25),
    (1469, 894, 49),
    (-704, -2, 313.5),
    (-704, -125, 375),
    (-704, 121, 375),
    (-554, 121, 375),
    (554, 2, 313.5),
    (-554, -125, 375),
    (554, -121, 375),
    (554, 125, 375),
    (-554, -2, 313.5),
    (704, 2, 313.5),
    (704, -121, 375),
    (-1564, 1380.8, 106.17),
    (-1564, 1003.28, 90.24),
    (1506.7, 930.24, 64.89),
    (211, -80, 67),
    (-211, 144, 67),
    (211, 144, 67),
    (-211, -336, 67),
    (-211, -80, 67),
    (211, -336, 67),
    (211, 400, 67),
    (-223, 399, 67),
    (-223, 143, 67),
    (214, -337, 67),
    (-223, -81, 67),
    (214, 399, 67),
    (214, -81, 67),
    (-223, -337, 67),
    (214, 143, 67),
    (-482, -2, 375),
    (-1552, 844.5, 106),
    (223.214, -149, 120.214),
    (-219.643, -149, 66.214),
    (-208, 336, 64),
    (482, 2, 375),
    (-1564, 411.47, 105.02),
    (-1564, 169.94, 105.02),
    (-1661, 424, 17),
    (-1683, 761, 17),
    (-1579, 488, 17),
    (317.5, 1391.5, 17),
    (1172.5, 761, 17),
    (460.75, 1304, 1),
    (-355, 1320, 1),
    (-243.25, 1080, 1),
    (-1299.25, 1080, 1),
    (258.25, 856, 1),
    (268.999, 920, 1),
    (332.75, 952, 1),
    (93, 600, 17),
    (220, 263, 17),
    (67.52, 600, 17),
    (365, 152, 17),
    (93, 8, 17),
    (296, 17, 88),
    (5.76, -488, 17),
    (220, -217, 17),
    (93, -280, 17),
    (557, -568, 17),
    (-532, 382, 264),
    (-269.75, 856, 1),
    (-275, 920, 1),
    (-195.25, 952, 1),
    (-84.74, 600, 17),
    (-220, 216.999, 17),
    (-157, 600, 17),
    (-212, 423, 56),
    (-205, 200, 17),
    (-28.48, -488, 17),
    (-220, -263, 17),
    (-205, -280, 17),
    (-125, -584, 17),
    (-357, -55, 17),
    (-1283.25, 1016, 1),
    (-1731.25, 968, 1),
    (-1165, 456, 17),
    (-1458, 741, 91),
]

SEARCH_RADIUS = 600  # units — typical light radius

with open(VMF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# Parse all light entities (light, light_spot, env_fire have light styles)
# env_fire and env_sprite with named rendercolor also contribute
LIGHT_CLASSES = {'light', 'light_spot', 'env_fire', 'env_laser'}

entity_pat = re.compile(r'entity\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)

lights = []
for m in entity_pat.finditer(text):
    body = m.group(1)
    cn_m = re.search(r'"classname"\s+"([^"]+)"', body)
    if not cn_m:
        continue
    cn = cn_m.group(1)
    if cn not in LIGHT_CLASSES:
        continue
    orig_m = re.search(r'"origin"\s+"([^"]+)"', body)
    if not orig_m:
        continue
    try:
        ox, oy, oz = map(float, orig_m.group(1).split())
    except:
        continue
    tn_m = re.search(r'"targetname"\s+"([^"]+)"', body)
    tn = tn_m.group(1) if tn_m else None
    lights.append((cn, tn, ox, oy, oz))

print(f"Total named light-style entities: {sum(1 for l in lights if l[1])}")
print(f"Total static (no targetname):     {sum(1 for l in lights if not l[1])}")
print()

# Cluster warning coords and find which have >4 named lights nearby
CLUSTER_RADIUS = 200
seen = set()
problem_zones = []

for wx, wy, wz in WARN_COORDS:
    key = (round(wx/100)*100, round(wy/100)*100, round(wz/100)*100)
    if key in seen:
        continue
    seen.add(key)
    nearby_named = []
    nearby_static = []
    for cn, tn, ox, oy, oz in lights:
        dist = math.sqrt((ox-wx)**2 + (oy-wy)**2 + (oz-wz)**2)
        if dist <= SEARCH_RADIUS:
            if tn:
                nearby_named.append((cn, tn, ox, oy, oz, round(dist)))
            else:
                nearby_static.append((cn, ox, oy, oz, round(dist)))
    if nearby_named:
        problem_zones.append((wx, wy, wz, nearby_named, nearby_static))

print(f"Distinct problem zones: {len(problem_zones)}")
print()
for wx, wy, wz, named, static in sorted(problem_zones, key=lambda z: -len(z[3])):
    print(f"  Zone ({wx:.0f}, {wy:.0f}, {wz:.0f})  named={len(named)} static={len(static)}")
    for cn, tn, ox, oy, oz, dist in sorted(named, key=lambda x: x[5])[:8]:
        print(f"    [{cn:12s}] targetname={tn:30s} @ ({ox:.0f},{oy:.0f},{oz:.0f}) dist={dist}")
    if len(named) > 8:
        print(f"    ... and {len(named)-8} more named")
    print()
