"""
cap_apt_light_distance.py
Sets _distance to 350 on all lights_apt*_on_light entities.
Apartments are ~450 units center-to-center; 350 covers the interior
without bleeding a light style slot into the shared corridor.
"""
import re, shutil

SRC = "rp_richland26.vmf"
BAK = "rp_richland26.vmf.bak_before_apt_distance"
NEW_DIST = 350

APT_LIGHT_PAT = re.compile(r'lights_apt\d+_on_light')

shutil.copy(SRC, BAK)
print(f"Backed up → {BAK}")

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

out = []
i = 0
changed = 0

while i < len(lines):
    line = lines[i]
    if line.strip() == 'entity':
        block = [line]; i += 1
        if i < len(lines): block.append(lines[i]); i += 1
        depth = 1
        while i < len(lines) and depth > 0:
            block.append(lines[i])
            s = lines[i].strip()
            if s == '{': depth += 1
            elif s == '}': depth -= 1
            i += 1
        block_text = ''.join(block)
        if '"classname" "light"' in block_text and APT_LIGHT_PAT.search(block_text):
            block_text = re.sub(
                r'"_distance"\s+"[^"]*"',
                f'"_distance" "{NEW_DIST}"',
                block_text
            )
            changed += 1
        out.append(block_text)
        continue
    out.append(line)
    i += 1

print(f"Set _distance={NEW_DIST} on {changed} apt light entities")

with open(SRC, "w", encoding="utf-8") as f:
    f.writelines(out)

print(f"Written → {SRC}")
