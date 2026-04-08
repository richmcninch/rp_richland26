import re
with open('rp_richland26.vmf', 'r', encoding='utf-8', errors='replace') as f:
    text = f.read()
entity_pat = re.compile(r'entity\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', re.DOTALL)
for m in entity_pat.finditer(text):
    body = m.group(1)
    cn = re.search(r'"classname"\s+"([^"]+)"', body)
    tn = re.search(r'"targetname"\s+"([^"]+)"', body)
    if not cn or not tn: continue
    if 'fridge' not in tn.group(1): continue
    dist = re.search(r'"_distance"\s+"([^"]+)"', body)
    attn_c = re.search(r'"_constant_attn"\s+"([^"]+)"', body)
    attn_l = re.search(r'"_linear_attn"\s+"([^"]+)"', body)
    attn_q = re.search(r'"_quadratic_attn"\s+"([^"]+)"', body)
    print(
        f"{tn.group(1):20s}  "
        f"_distance={dist.group(1) if dist else '(none)':8s}  "
        f"const={attn_c.group(1) if attn_c else 'none'}  "
        f"lin={attn_l.group(1) if attn_l else 'none'}  "
        f"quad={attn_q.group(1) if attn_q else 'none'}"
    )
