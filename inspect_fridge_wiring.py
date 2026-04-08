import re
vmf = open('rp_richland26.vmf', encoding='utf-8', errors='replace').read()

# Find worldspawn skyname
ws = re.search(r'"classname"\s+"worldspawn".*?"skyname"\s+"([^"]+)"', vmf, re.DOTALL)
print('Current sky:', ws.group(1) if ws else 'not found')

# Find all outputs that target fridge*light
out_re = re.compile(r'"(\w+)"\s+"(fridge\d+light,[^"]+)"')
print('\nOutputs targeting fridge lights:')
for name, val in out_re.findall(vmf):
    print(f'  {name} -> {val}')

# Also find what entities contain those outputs (to get their classnames)
ent_blk = re.compile(r'entity\s*\{(.*?)\n\}', re.DOTALL)
kv = re.compile(r'"(\w+)"\s+"([^"]+)"')
for m in ent_blk.finditer(vmf):
    body = m.group(1)
    if re.search(r'fridge\d+light', body):
        d = dict(kv.findall(body))
        cn = d.get('classname', '?')
        tn = d.get('targetname', '?')
        origin = d.get('origin', '?')
        outputs = [(k, v) for k, v in kv.findall(body) if 'fridge' in v.lower()]
        if outputs:
            print(f'\n  Entity: {cn} targetname={tn} origin={origin}')
            for k, v in outputs:
                print(f'    {k} = {v}')
