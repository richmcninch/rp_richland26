import re

VMF = "rp_richland26.vmf"

with open(VMF, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Parse solids and their sides with dispinfo
solid_pat = re.compile(r'solid\s*\{\s*"id"\s*"(\d+)"(.*?)\n\t\}', re.DOTALL)
side_pat   = re.compile(r'side\s*\{(.*?)\n\t\t\}', re.DOTALL)
disp_pat   = re.compile(r'dispinfo\s*\{(.*?)\n\t\t\t\}', re.DOTALL)

power4 = []
power3 = []

for solid_m in solid_pat.finditer(content):
    solid_id  = solid_m.group(1)
    solid_body = solid_m.group(2)
    for side_m in side_pat.finditer(solid_body):
        side_body = side_m.group(1)
        disp_m = disp_pat.search(side_body)
        if not disp_m:
            continue
        disp_body = disp_m.group(1)
        power_m   = re.search(r'"power"\s+"(\d+)"', disp_body)
        start_m   = re.search(r'"startposition"\s+"\[([^\]]+)\]"', disp_body)
        plane_m   = re.search(r'"plane"\s+"\(([^)]+)\)', side_body)
        power = int(power_m.group(1)) if power_m else 0
        start = start_m.group(1).strip() if start_m else "?"
        plane = plane_m.group(1).strip() if plane_m else "?"
        entry = (power, solid_id, start, plane)
        if power >= 4:
            power4.append(entry)
        elif power == 3:
            power3.append(entry)

print(f"Power-4 displacements: {len(power4)}")
print(f"Power-3 displacements: {len(power3)}")
print()

# Sort by X position to cluster spatially
def start_xyz(e):
    try:
        parts = e[2].split()
        return float(parts[0]), float(parts[1]), float(parts[2])
    except:
        return (0,0,0)

power4.sort(key=start_xyz)

print("=== Power-4 displacements (sorted by X,Y,Z) ===")
print(f"{'SolidID':>8}  {'StartPos':>40}  FirstPlaneVert")
for power, sid, start, plane in power4:
    print(f"{sid:>8}  {start:>40}  {plane[:40]}")
