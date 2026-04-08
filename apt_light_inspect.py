import re

VMF = "rp_richland26.vmf"
with open(VMF, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

entity_pat = re.compile(r'entity\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)

apt_lights = {}
for m in entity_pat.finditer(text):
    body = m.group(1)
    cn_m = re.search(r'"classname"\s+"([^"]+)"', body)
    if not cn_m or cn_m.group(1) != 'light':
        continue
    tn_m = re.search(r'"targetname"\s+"([^"]+)"', body)
    if not tn_m or 'apt' not in tn_m.group(1):
        continue
    tn = tn_m.group(1)
    orig_m = re.search(r'"origin"\s+"([^"]+)"', body)
    light_m = re.search(r'"_light"\s+"([^"]+)"', body)
    zero_m = re.search(r'"_zero_percent_distance"\s+"([^"]+)"', body)
    fifty_m = re.search(r'"_fifty_percent_distance"\s+"([^"]+)"', body)
    apt_lights.setdefault(tn, []).append({
        'origin': orig_m.group(1) if orig_m else '?',
        '_light': light_m.group(1) if light_m else '(default)',
        '_zero': zero_m.group(1) if zero_m else None,
        '_fifty': fifty_m.group(1) if fifty_m else None,
    })

for tn, lights in sorted(apt_lights.items()):
    print(f"\n{tn}  ({len(lights)} lights)")
    for l in lights[:4]:
        zero = f"  zero={l['_zero']}" if l['_zero'] else ""
        fifty = f"  fifty={l['_fifty']}" if l['_fifty'] else ""
        print(f"  @ {l['origin']:30s}  _light={l['_light']}{zero}{fifty}")
    if len(lights) > 4:
        print(f"  ... +{len(lights)-4} more")
