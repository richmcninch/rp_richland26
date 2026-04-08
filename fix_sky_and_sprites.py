"""
1. Change skyname sky_day02_04 -> sky_day01_01 in worldspawn.
2. Add env_sprite glow inside each fridge, wired to the fridge door outputs.

Fridge door fires: OnOpen -> fridge#light TurnOn
                   OnFullyClosed -> fridge#light TurnOff
We add:           OnOpen -> fridge#glow ShowSprite
                   OnFullyClosed -> fridge#glow HideSprite

VMF output format: "targetname\x1binput\x1bparam\x1bdelay\x1btimes"
"""
import re, shutil

SEP = '\x1b'
vmf_path = 'rp_richland26.vmf'
shutil.copy(vmf_path, vmf_path + '.bak_before_sprite')
print(f'Backed up -> {vmf_path}.bak_before_sprite')

text = open(vmf_path, encoding='utf-8', errors='replace').read()

# ── 1. Fix skyname ────────────────────────────────────────────────────────────
OLD_SKY = 'sky_day02_04'
NEW_SKY = 'sky_day01_01'
if OLD_SKY in text:
    text = text.replace(f'"skyname" "{OLD_SKY}"', f'"skyname" "{NEW_SKY}"')
    print(f'Sky: {OLD_SKY} -> {NEW_SKY}')
else:
    print(f'WARNING: {OLD_SKY} not found in VMF')

# ── 2. Read fridge light positions ───────────────────────────────────────────
ent_re = re.compile(r'entity\s*\{(.*?)\n\}', re.DOTALL)
kv_re  = re.compile(r'"(\w+)"\s+"([^"]+)"')

fridge_lights = {}   # num -> (x, y, z)
for m in ent_re.finditer(text):
    d = dict(kv_re.findall(m.group(1)))
    tn = d.get('targetname', '')
    mm = re.match(r'fridge(\d+)light$', tn)
    if mm and d.get('classname') == 'light' and 'origin' in d:
        n = mm.group(1)
        x, y, z = map(float, d['origin'].split())
        fridge_lights[n] = (x, y, z)

print(f'Found {len(fridge_lights)} fridge lights: {sorted(fridge_lights)}')

# ── 3. Add ShowSprite/HideSprite outputs to fridge doors ─────────────────────
def patch_door(m):
    body = m.group(1)
    d = dict(kv_re.findall(body))
    tn = d.get('targetname', '')
    mm = re.match(r'fridge(\d+)door2$', tn)
    if not mm or d.get('classname') != 'func_door_rotating':
        return m.group(0)

    n = mm.group(1)
    sprite_name = f'fridge{n}glow'

    show_line = f'\t\t"OnOpen" "fridge{n}glow{SEP}ShowSprite{SEP}{SEP}0{SEP}-1"'
    hide_line = f'\t\t"OnFullyClosed" "fridge{n}glow{SEP}HideSprite{SEP}{SEP}0{SEP}-1"'

    # Already patched?
    if sprite_name in body:
        return m.group(0)

    # Insert new outputs inside the connections block
    conn_re = re.compile(r'(connections\s*\{)(.*?)(\n\t\})', re.DOTALL)
    def add_outputs(cm):
        return cm.group(1) + cm.group(2) + '\n' + show_line + '\n' + hide_line + cm.group(3)

    new_body = conn_re.sub(add_outputs, body)
    return m.group(0).replace(body, new_body)

text = ent_re.sub(patch_door, text)
print('Added ShowSprite/HideSprite outputs to fridge doors')

# ── 4. Find max entity id ─────────────────────────────────────────────────────
ids = [int(x) for x in re.findall(r'"id" "(\d+)"', text)]
next_id = max(ids) + 1
print(f'Starting new entity IDs at {next_id}')

# ── 5. Build env_sprite entities ─────────────────────────────────────────────
sprite_blocks = []
for n, (x, y, z) in sorted(fridge_lights.items()):
    eid = next_id
    next_id += 1
    block = f'''entity
{{
\t"id" "{eid}"
\t"classname" "env_sprite"
\t"targetname" "fridge{n}glow"
\t"origin" "{x} {y} {z}"
\t"model" "sprites/light_glow01_noz.vmt"
\t"scale" "0.3"
\t"rendermode" "5"
\t"rendercolor" "200 220 255"
\t"renderamt" "180"
\t"spawnflags" "0"
\teditor
\t{{
\t\t"color" "0 220 255"
\t\t"visgroupshown" "1"
\t\t"visgroupautoshown" "1"
\t}}
}}'''
    sprite_blocks.append(block)
    print(f'  env_sprite fridge{n}glow at ({x}, {y}, {z})')

# Append entities before end of file
text = text.rstrip() + '\n' + '\n'.join(sprite_blocks) + '\n'

open(vmf_path, 'w', encoding='utf-8').write(text)
print(f'\nWritten -> {vmf_path}')
