"""
Convert lights_apt*_on_light entities from baked 'light' to 'light_dynamic'.

Baked lights consume one light style slot per unique targetname on every face
within _distance. With 8 apt groups and corridor faces shared between apts,
the Source Engine limit of 4 styles/face is exceeded on 121 faces.

light_dynamic entities are rendered at runtime by the engine — they are
completely invisible to vrad/bspzip and consume no style slots at all.
Per-apartment TurnOn/TurnOff input logic continues to work unchanged.

Changes per entity:
  classname  light -> light_dynamic
  _distance  -> distance (light_dynamic key name), set to 500
  style      removed (not applicable to dynamic lights)
"""
import re, shutil

vmf_path = 'rp_richland26.vmf'
shutil.copy(vmf_path, vmf_path + '.bak_before_dynamic')
print(f'Backed up -> {vmf_path}.bak_before_dynamic')

text = open(vmf_path, encoding='utf-8', errors='replace').read()
ent_re = re.compile(r'(entity\s*\{)(.*?)(\n\})', re.DOTALL)
kv_re = re.compile(r'"(\w+)"\s+"([^"]+)"')

converted = 0

def convert_entity(m):
    global converted
    prefix, body, suffix = m.group(1), m.group(2), m.group(3)
    d = dict(kv_re.findall(body))

    if d.get('classname') != 'light':
        return m.group(0)
    tn = d.get('targetname', '')
    if not re.match(r'lights_apt\d+_on_light$', tn):
        return m.group(0)

    # classname: light -> light_dynamic
    new_body = re.sub(r'"classname"\s+"light"', '"classname" "light_dynamic"', body)
    # _distance -> distance with a runtime-appropriate range
    if '"_distance"' in new_body:
        new_body = re.sub(r'"_distance"\s+"[^"]+"', '"distance" "500"', new_body)
    else:
        new_body = new_body.rstrip('\t ') + '\n\t\t"distance" "500"\n\t'
    # Remove style key — light_dynamic doesn't use baked styles
    new_body = re.sub(r'\t*"style"\s+"[^"]+"\r?\n', '', new_body)

    converted += 1
    return prefix + new_body + suffix

new_text = ent_re.sub(convert_entity, text)

open(vmf_path, 'w', encoding='utf-8').write(new_text)
print(f'Converted {converted} apt light entities -> light_dynamic')
print(f'Written  -> {vmf_path}')
