"""
unique_styles_audit.py — shows how many DISTINCT targetnames hit each problem zone
"""
import re, math

VMF = "rp_richland26.vmf"

# Rerun from last compile - just need to check which distinct names hit each zone
# Representative problem zones (deduplicated)
WARN_ZONES = [
    (-704, -2, 314, "apt_corridor"),
    (24.9, 858.5, 17, "exterior_N"),
    (-1352, 848.5, 17, "exterior_NW"),
    (74.9, -48, 17, "plaza"),
    (-78.3, -59.7, 17, "plaza2"),
    (1466, 942, 65, "zone_NE"),
    (-532, 302, 104, "stairwell?"),
    (-1564, 1380.8, 106, "exterior_NW2"),
    (211, -80, 67, "z67_block"),
    (-482, -2, 375, "apt_roof"),
    (-357, -55, 17, "street_E"),
    (93, 600, 17, "street_N"),
    (-1661, 424, 17, "exterior_W"),
]

SEARCH_RADIUS = 500

LIGHT_CLASSES = {'light', 'light_spot', 'env_fire', 'env_laser'}

with open(VMF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

entity_pat = re.compile(r'entity\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)
lights = []
for m in entity_pat.finditer(text):
    body = m.group(1)
    cn_m = re.search(r'"classname"\s+"([^"]+)"', body)
    if not cn_m or cn_m.group(1) not in LIGHT_CLASSES:
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
    lights.append((cn_m.group(1), tn, ox, oy, oz))

print(f"{'Zone':20s}  {'Unique styles':>13}  {'Named lights':>12}  Top names")
print("-" * 90)
for wx, wy, wz, label in WARN_ZONES:
    unique_names = set()
    named_near = []
    for cn, tn, ox, oy, oz in lights:
        dist = math.sqrt((ox-wx)**2 + (oy-wy)**2 + (oz-wz)**2)
        if dist <= SEARCH_RADIUS and tn:
            unique_names.add(tn)
            named_near.append((tn, cn, round(dist)))
    top = sorted(unique_names)[:5]
    top_str = ', '.join(top)
    print(f"{label:20s}  {len(unique_names):>13}  {len(named_near):>12}  {top_str}")
