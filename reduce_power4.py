"""
reduce_power4.py
Downsample all power-4 displacements in rp_richland26.vmf to power-3.

Power-4 grid: 17x17 vertices (normals/distances/offsets/alphas), 16x32 triangle_tags
Power-3 grid:  9x9 vertices,                                       8x16 triangle_tags
Strategy: subsample by taking every other row and every other column/value.
"""
import re, shutil

SRC = 'rp_richland26.vmf'
BAK = 'rp_richland26.vmf.bak_before_disp_reduce'

N_OLD = 17   # 2^4 + 1
N_NEW = 9    # 2^3 + 1
STEP  = 2

# triangle_tags dimensions (empirically confirmed)
TT_ROWS_OLD = 16  # 2^4
TT_VALS_OLD = 32  # 2 * 2^4
TT_ROWS_NEW = 8   # 2^3
TT_VALS_NEW = 16  # 2 * 2^3


def downsample_vec3_row(s):
    v = s.split()
    return ' '.join(v[i*3:i*3+3][j] for i in range(0, N_OLD, STEP) for j in range(3))


def downsample_scalar_row(s):
    v = s.split()
    return ' '.join(v[i] for i in range(0, N_OLD, STEP))


def collect_subblock(lines, start):
    """Collect from lines[start] (the '{' line) through matching '}'. Returns (block, next_i)."""
    assert lines[start].strip() == '{'
    result = [lines[start]]
    depth = 1
    i = start + 1
    while i < len(lines) and depth > 0:
        result.append(lines[i])
        s = lines[i].strip()
        if s == '{':
            depth += 1
        elif s == '}':
            depth -= 1
        i += 1
    return result, i


def rewrite_dispinfo(block):
    """block: list of lines from '{' to '}' of a dispinfo. Returns transformed list."""
    if not any('"power" "4"' in l for l in block):
        return block

    out = []
    i = 0
    while i < len(block):
        line = block[i]
        stripped = line.strip()

        if '"power" "4"' in line:
            out.append(line.replace('"power" "4"', '"power" "3"'))
            i += 1
            continue

        if stripped in ('normals', 'distances', 'offsets', 'offset_normals',
                        'alphas', 'triangle_tags', 'allowed_verts'):
            name = stripped
            out.append(line)  # the name keyword line
            i += 1
            sub, i = collect_subblock(block, i)
            # sub[0]='{', sub[-1]='}'
            row_indent = re.match(r'(\s*)', sub[0]).group(1) + '\t'
            inner = sub[1:-1]

            if name in ('normals', 'offsets', 'offset_normals'):
                rows = {}
                for l in inner:
                    m = re.match(r'\s*"row(\d+)"\s+"([^"]+)"', l)
                    if m:
                        rows[int(m.group(1))] = m.group(2)
                out.append(sub[0])
                for new_r, old_r in enumerate(range(0, N_OLD, STEP)):
                    data = rows.get(old_r, ('0 0 1 ' * N_OLD).strip())
                    out.append(f'{row_indent}"row{new_r}" "{downsample_vec3_row(data)}"\n')
                out.append(sub[-1])

            elif name in ('distances', 'alphas'):
                rows = {}
                for l in inner:
                    m = re.match(r'\s*"row(\d+)"\s+"([^"]+)"', l)
                    if m:
                        rows[int(m.group(1))] = m.group(2)
                out.append(sub[0])
                for new_r, old_r in enumerate(range(0, N_OLD, STEP)):
                    data = rows.get(old_r, ('0 ' * N_OLD).strip())
                    out.append(f'{row_indent}"row{new_r}" "{downsample_scalar_row(data)}"\n')
                out.append(sub[-1])

            elif name == 'triangle_tags':
                rows = {}
                for l in inner:
                    m = re.match(r'\s*"row(\d+)"\s+"([^"]+)"', l)
                    if m:
                        rows[int(m.group(1))] = m.group(2)
                out.append(sub[0])
                for new_r in range(TT_ROWS_NEW):
                    old_r = new_r * 2
                    if old_r in rows:
                        v = rows[old_r].split()
                        new_vals = [v[j] for j in range(0, TT_VALS_OLD, 2)]
                    else:
                        new_vals = ['9'] * TT_VALS_NEW
                    out.append(f'{row_indent}"row{new_r}" "{" ".join(new_vals)}"\n')
                out.append(sub[-1])

            else:
                # allowed_verts and anything else: pass through unchanged
                out.extend(sub)

            continue

        out.append(line)
        i += 1

    return out


# ── main ─────────────────────────────────────────────────────────────────────

shutil.copy(SRC, BAK)
print(f'Backed up → {BAK}')

with open(SRC, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

result = []
i = 0
changed = 0

while i < len(lines):
    line = lines[i]
    if line.strip() == 'dispinfo':
        result.append(line)
        i += 1
        if i < len(lines) and lines[i].strip() == '{':
            block, i = collect_subblock(lines, i)
            transformed = rewrite_dispinfo(block)
            if transformed is not block:
                changed += 1
            result.extend(transformed)
        continue
    result.append(line)
    i += 1

print(f'Transformed {changed} dispinfo blocks from power-4 → power-3')

with open(SRC, 'w', encoding='utf-8') as f:
    f.writelines(result)

print(f'Written → {SRC}')
