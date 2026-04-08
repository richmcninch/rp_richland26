import re
vmf = open('rp_richland26.vmf', encoding='utf-8', errors='replace').read()

# Find func_door_rotating blocks containing fridge1door2
ent_re = re.compile(r'entity\s*\{(.*?)\n\}', re.DOTALL)
for m in ent_re.finditer(vmf):
    body = m.group(1)
    if 'fridge1door2' in body and 'func_door_rotating' in body:
        print("=== fridge1door2 entity ===")
        for line in body.split('\n'):
            line = line.strip()
            if line:
                print(' ', repr(line))
        break
