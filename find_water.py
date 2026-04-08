import re
text = open('rp_richland26.vmf', encoding='utf-8', errors='replace').read()
hits = re.findall(r'"material"\s+"[^"]*water[^"]*"', text, re.IGNORECASE)
for h in hits:
    print(h)
print(f'\nTotal: {len(hits)}')
# Also check for dev_water
dev = re.findall(r'"material"\s+"[^"]*dev[^"]*"', text, re.IGNORECASE)
for d in dev[:10]:
    print(d)
