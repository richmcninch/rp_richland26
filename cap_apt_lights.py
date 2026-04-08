"""
cap_apt_lights.py
Sets _zero_percent_distance and _fifty_percent_distance on all lights_apt*_on_light
entities to prevent light bleed across apartment walls into shared corridors.
"""
import re, shutil

SRC = "rp_richland26.vmf"
BAK = "rp_richland26.vmf.bak_before_lightcap"

ZERO_DIST  = 300   # hard cutoff distance
FIFTY_DIST = 160   # 50% brightness distance (smooth falloff within room)

# These are the named groups we want to cap
APT_PATTERN = re.compile(r'lights_apt\d+_on_light')

shutil.copy(SRC, BAK)
print(f"Backed up → {BAK}")

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

# We'll replace entity blocks one at a time
# Match each entity block
entity_pat = re.compile(r'(entity\s*\{)((?:[^{}]|\{[^{}]*\})*?)(\n\})', re.DOTALL)

changed = 0

def patch_entity(m):
    global changed
    open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
    cn_m = re.search(r'"classname"\s+"([^"]+)"', body)
    if not cn_m or cn_m.group(1) != 'light':
        return m.group(0)
    tn_m = re.search(r'"targetname"\s+"([^"]+)"', body)
    if not tn_m or not APT_PATTERN.search(tn_m.group(1)):
        return m.group(0)

    # Replace existing zero/fifty distance values (already present as "0")
    new_body = re.sub(
        r'"_zero_percent_distance"\s+"[^"]*"',
        f'"_zero_percent_distance" "{ZERO_DIST}"',
        body
    )
    new_body = re.sub(
        r'"_fifty_percent_distance"\s+"[^"]*"',
        f'"_fifty_percent_distance" "{FIFTY_DIST}"',
        new_body
    )

    # If they weren't present at all, insert before closing brace of entity body
    if '"_zero_percent_distance"' not in new_body:
        new_body = new_body.rstrip() + f'\n\t"_zero_percent_distance" "{ZERO_DIST}"\n'
    if '"_fifty_percent_distance"' not in new_body:
        new_body = new_body.rstrip() + f'\n\t"_fifty_percent_distance" "{FIFTY_DIST}"\n'

    if new_body != body:
        changed += 1
    return open_tag + new_body + close_tag

new_text = entity_pat.sub(patch_entity, text)

print(f"Patched {changed} apartment light entities")

with open(SRC, "w", encoding="utf-8") as f:
    f.write(new_text)

print(f"Written → {SRC}")
