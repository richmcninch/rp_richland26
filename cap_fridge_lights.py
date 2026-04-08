"""
cap_fridge_lights.py
Adds tight range limits to all fridge*light entities so they can't bleed
across walls into corridors. A fridge interior is ~32 units deep; 80 unit
hard cutoff keeps the glow nice and local.
"""
import re, shutil

SRC  = "rp_richland26.vmf"
BAK  = "rp_richland26.vmf.bak_before_fridgecap"

ZERO_DIST  = 80   # hard cutoff — just enough to spill onto the floor in front
FIFTY_DIST = 48   # 50% brightness distance

FRIDGE_PAT = re.compile(r'fridge\d+light')

shutil.copy(SRC, BAK)
print(f"Backed up → {BAK}")

with open(SRC, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

out = []
i = 0
changed = 0

while i < len(lines):
    line = lines[i]
    # Look for start of an entity block
    if line.strip() == 'entity':
        # Collect the full entity block
        block = [line]
        i += 1
        # expect '{'
        if i < len(lines):
            block.append(lines[i]); i += 1
        depth = 1
        while i < len(lines) and depth > 0:
            block.append(lines[i])
            s = lines[i].strip()
            if s == '{': depth += 1
            elif s == '}': depth -= 1
            i += 1

        block_text = ''.join(block)

        is_light     = '"classname" "light"' in block_text
        is_fridge    = bool(FRIDGE_PAT.search(block_text))

        if is_light and is_fridge:
            has_zero  = '"_zero_percent_distance"'  in block_text
            has_fifty = '"_fifty_percent_distance"' in block_text

            if has_zero:
                block_text = re.sub(
                    r'"_zero_percent_distance"\s+"[^"]*"',
                    f'"_zero_percent_distance" "{ZERO_DIST}"',
                    block_text
                )
            if has_fifty:
                block_text = re.sub(
                    r'"_fifty_percent_distance"\s+"[^"]*"',
                    f'"_fifty_percent_distance" "{FIFTY_DIST}"',
                    block_text
                )

            # Insert missing keys before the closing 'editor' block or final '}'
            if not has_zero or not has_fifty:
                insert = ""
                if not has_zero:
                    insert += f'\t"_zero_percent_distance" "{ZERO_DIST}"\n'
                if not has_fifty:
                    insert += f'\t"_fifty_percent_distance" "{FIFTY_DIST}"\n'
                # Insert before the 'editor' sub-block if present, else before last '}'
                if '\teditor\n' in block_text:
                    block_text = block_text.replace('\teditor\n', insert + '\teditor\n', 1)
                else:
                    block_text = block_text.rstrip().rstrip('}') + '\n' + insert + '}\n'

            out.append(block_text)
            changed += 1
            continue

        out.append(block_text)
        continue

    out.append(line)
    i += 1

print(f"Patched {changed} fridge light entities")

with open(SRC, "w", encoding="utf-8") as f:
    f.writelines(out)

print(f"Written → {SRC}")
