import re
with open('rp_richland26.vmf', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
entity_pat = re.compile(r'entity\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)
seen = {}
for m in entity_pat.finditer(text):
    body = m.group(1)
    cn = re.search(r'"classname"\s+"([^"]+)"', body)
    tn = re.search(r'"targetname"\s+"([^"]+)"', body)
    if not cn or not tn: continue
    if 'apt' not in tn.group(1): continue
    name = tn.group(1)
    if name in seen: continue
    seen[name] = True
    dist = re.search(r'"_distance"\s+"([^"]+)"', body)
    orig = re.search(r'"origin"\s+"([^"]+)"', body)
    print(f"{name:35s}  _distance={dist.group(1) if dist else '(none)':8s}  @ {orig.group(1) if orig else '?'}")
