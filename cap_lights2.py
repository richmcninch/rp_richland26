"""
Lower apt lights to _distance=250 (ceiling faces are 263+u away -> excluded).
Cap office lights at _distance=400 (currently unlimited=0, causing global reach).
"""
import re, shutil, os

vmf_path = 'rp_richland26.vmf'
shutil.copy(vmf_path, vmf_path + '.bak_before_cap2')
print(f'Backed up -> {vmf_path}.bak_before_cap2')

text = open(vmf_path, encoding='utf-8', errors='replace').read()

# Find all entity blocks and patch in-place
ent_re = re.compile(r'(entity\s*\{)(.*?)(\n\})', re.DOTALL)
kv_re = re.compile(r'"(\w+)"\s+"([^"]+)"')

apt_count = 0
office_count = 0

def patch_entity(m):
    global apt_count, office_count
    prefix, body, suffix = m.group(1), m.group(2), m.group(3)
    d = dict(kv_re.findall(body))
    classname = d.get('classname', '')
    targetname = d.get('targetname', '')

    if classname != 'light':
        return m.group(0)

    if re.match(r'lights_apt\d+_on_light$', targetname):
        # Lower to 250
        if '"_distance"' in body:
            new_body = re.sub(r'"_distance"\s+"[^"]+"', '"_distance" "250"', body)
        else:
            new_body = body.rstrip() + '\n\t\t"_distance" "250"\n\t'
        apt_count += 1
        return prefix + new_body + suffix

    if targetname == 'lights_office_on_light':
        # Cap unlimited lights at 400
        if '"_distance"' in body:
            new_body = re.sub(r'"_distance"\s+"[^"]+"', '"_distance" "400"', body)
        else:
            new_body = body.rstrip() + '\n\t\t"_distance" "400"\n\t'
        office_count += 1
        return prefix + new_body + suffix

    return m.group(0)

new_text = ent_re.sub(patch_entity, text)

open(vmf_path, 'w', encoding='utf-8').write(new_text)
print(f'Set _distance=250 on {apt_count} apt light entities')
print(f'Set _distance=400 on {office_count} office light entities')
print(f'Written -> {vmf_path}')
