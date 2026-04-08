import re
with open('rp_richland26.vmf', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
entity_pat = re.compile(r'entity\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)
for m in entity_pat.finditer(text):
    body = m.group(1)
    cn_m = re.search(r'"classname"\s+"([^"]+)"', body)
    tn_m = re.search(r'"targetname"\s+"([^"]+)"', body)
    if not cn_m or not tn_m: continue
    if 'fridge' not in tn_m.group(1): continue
    orig  = re.search(r'"origin"\s+"([^"]+)"', body)
    light = re.search(r'"_light"\s+"([^"]+)"', body)
    zero  = re.search(r'"_zero_percent_distance"\s+"([^"]+)"', body)
    fifty = re.search(r'"_fifty_percent_distance"\s+"([^"]+)"', body)
    print(
        f"{tn_m.group(1):20s}  {cn_m.group(1):12s}  "
        f"origin={orig.group(1) if orig else '?':30s}  "
        f"_light={light.group(1) if light else '(default)':20s}  "
        f"zero={zero.group(1) if zero else 'none'}  "
        f"fifty={fifty.group(1) if fifty else 'none'}"
    )
