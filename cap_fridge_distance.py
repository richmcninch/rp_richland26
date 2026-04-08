"""
cap_fridge_distance.py
Sets _distance to 96 on all fridge*light entities so vrad
stops assigning their light style slot to faces outside the kitchen.
"""
import re, shutil

SRC = "rp_richland26.vmf"
BAK = "rp_richland26.vmf.bak_before_fridge_distance"
NEW_DIST = 96

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
        if '"classname" "light"' in block_text and re.search(r'fridge\d+light', block_text):
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

print(f"Set _distance={NEW_DIST} on {changed} fridge light entities")

with open(SRC, "w", encoding="utf-8") as f:
    f.writelines(out)

print(f"Written → {SRC}")
