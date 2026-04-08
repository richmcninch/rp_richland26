"""
vmf_mcp.py — MCP server for rp_richland26 VMF manipulation.

Tools exposed to Copilot/Claude:
  vmf_audit          — list all richbot_spawn entities and their positions
  vmf_get_entities   — query entities by classname and/or targetname pattern
  vmf_set_origin     — move an entity by targetname
  vmf_add_entity     — add a new entity block
  vmf_remove_entity  — remove an entity by targetname
  vmf_compile        — run vbsp/vvis/vrad and copy BSP to server + client

Run via:  python vmf_mcp.py
VS Code mcp.json:
  { "servers": { "vmf": { "type": "stdio", "command": "python", "args": ["F:/richbots/rp_richland26/vmf_mcp.py"] } } }
"""

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────

VMF_PATH      = Path(__file__).parent / "rp_richland26.vmf"
GMOD_BIN      = Path(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64")
GMOD_GAME     = Path(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod")
BSP_DEST      = Path(r"F:\richbots\server\garrysmod\maps\rp_richland26.bsp")
BSP_DEST_CLIENT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod\maps\rp_richland26.bsp")

mcp = FastMCP("vmf-richland2026")

# ── Raw VMF helpers ───────────────────────────────────────────────────────────

def _read() -> str:
    return VMF_PATH.read_text(encoding="utf-8", errors="replace")


def _write(text: str, backup: bool = True) -> str:
    if backup:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = VMF_PATH.with_name(f"rp_richland26.vmf.bak_{ts}")
        shutil.copy2(VMF_PATH, bak)
    VMF_PATH.write_text(text, encoding="utf-8")
    return "OK"


def _parse_entities(text: str) -> list[dict]:
    """Parse all top-level entity blocks into dicts."""
    entities = []
    for block in re.finditer(r'^entity\s*\{([^{}]*)\}', text, re.MULTILINE | re.DOTALL):
        body = block.group(1)
        props = dict(re.findall(r'"(\w+)"\s+"([^"]*)"', body))
        props["_span"] = (block.start(), block.end())
        entities.append(props)
    return entities


def _max_id(text: str) -> int:
    ids = [int(x) for x in re.findall(r'"id"\s+"(\d+)"', text)]
    return max(ids) if ids else 1


def _entity_block(props: dict, eid: int) -> str:
    lines = ['entity', '{', f'\t"id" "{eid}"']
    for k, v in props.items():
        if k == "_span":   # internal metadata only — NOT VMF KVPs like _light, _cone etc.
            continue
        lines.append(f'\t"{k}" "{v}"')
    lines.append('}')
    return "\n".join(lines) + "\n"


# ── Brush geometry ─────────────────────────────────────────────────────────────
# VMF plane convention: normal = (p2-p0) × (p1-p0) must point OUTWARD.
# Each tuple: (pts_fn(x1,y1,z1,x2,y2,z2)->3 points, uaxis, vaxis)
_FACE_DEFS = [
    # top    (+Z, z=z2)
    (lambda x1,y1,z1,x2,y2,z2: ((x2,y1,z2),(x1,y1,z2),(x1,y2,z2)), "[1 0 0 0] 0.25", "[0 -1 0 0] 0.25"),
    # bottom (-Z, z=z1)
    (lambda x1,y1,z1,x2,y2,z2: ((x2,y2,z1),(x1,y2,z1),(x1,y1,z1)), "[1 0 0 0] 0.25", "[0 -1 0 0] 0.25"),
    # -X wall (x=x1)
    (lambda x1,y1,z1,x2,y2,z2: ((x1,y1,z1),(x1,y2,z1),(x1,y2,z2)), "[0 1 0 0] 0.25", "[0 0 -1 0] 0.25"),
    # +X wall (x=x2)
    (lambda x1,y1,z1,x2,y2,z2: ((x2,y2,z1),(x2,y1,z1),(x2,y1,z2)), "[0 1 0 0] 0.25", "[0 0 -1 0] 0.25"),
    # -Y wall (y=y1)
    (lambda x1,y1,z1,x2,y2,z2: ((x2,y1,z1),(x1,y1,z1),(x1,y1,z2)), "[1 0 0 0] 0.25", "[0 0 -1 0] 0.25"),
    # +Y wall (y=y2)
    (lambda x1,y1,z1,x2,y2,z2: ((x1,y2,z1),(x2,y2,z1),(x2,y2,z2)), "[1 0 0 0] 0.25", "[0 0 -1 0] 0.25"),
]


def _side_block(sid: int, pts: tuple, material: str, uaxis: str, vaxis: str) -> str:
    a, b, c = pts
    plane = f"({a[0]} {a[1]} {a[2]}) ({b[0]} {b[1]} {b[2]}) ({c[0]} {c[1]} {c[2]})"
    return (
        f"\t\tside\n\t\t{{\n"
        f'\t\t\t"id" "{sid}"\n'
        f'\t\t\t"plane" "{plane}"\n'
        f'\t\t\t"material" "{material}"\n'
        f'\t\t\t"uaxis" "{uaxis}"\n'
        f'\t\t\t"vaxis" "{vaxis}"\n'
        f'\t\t\t"rotation" "0"\n'
        f'\t\t\t"lightmapscale" "16"\n'
        f'\t\t\t"smoothing_groups" "0"\n'
        f"\t\t}}\n"
    )


def _box_solid(x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
               material: str, bid: int, sid_start: int,
               face_materials: dict | None = None) -> tuple[str, int]:
    """
    Generate a VMF solid block for an AABB.
    Automatically normalizes so min < max on each axis.
    Raises ValueError if any dimension is < 4 units (would produce a degenerate brush).
    """
    # Normalize so x1 < x2 etc.
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    z1, z2 = min(z1, z2), max(z1, z2)
    if x2 - x1 < 4 or y2 - y1 < 4 or z2 - z1 < 4:
        raise ValueError(
            f"Degenerate brush: ({x1},{y1},{z1})→({x2},{y2},{z2}) — all dimensions must be ≥ 4 units"
        )
    # face_materials: optional per-face override keyed by 'top','bottom','x-','x+','y-','y+'
    face_names = ["top", "bottom", "x-", "x+", "y-", "y+"]
    lines = [f"\tsolid\n\t{{\n", f'\t\t"id" "{bid}"\n']
    sid = sid_start
    coords = (x1, y1, z1, x2, y2, z2)
    for name, (pts_fn, uaxis, vaxis) in zip(face_names, _FACE_DEFS):
        mat = (face_materials or {}).get(name, material)
        lines.append(_side_block(sid, pts_fn(*coords), mat, uaxis, vaxis))
        sid += 1
    lines.append(
        '\t\teditor\n\t\t{\n'
        '\t\t\t"color" "220 80 30"\n'
        '\t\t\t"visgroupshown" "1"\n'
        '\t\t\t"visgroupautoshown" "1"\n'
        '\t\t}\n'
    )
    lines.append("\t}\n")
    return "".join(lines), sid


def _insert_into_world(text: str, solid_text: str) -> str:
    """Append solid block(s) inside the world block, before its closing }."""
    m = re.search(r'^entity\b', text, re.MULTILINE)
    if m:
        end_world = text.rfind('\n}', 0, m.start())
        if end_world != -1:
            return text[:end_world + 1] + solid_text + text[end_world + 1:]
    # Fallback: no entities found, append before EOF's last }
    last = text.rfind('\n}')
    if last != -1:
        return text[:last + 1] + solid_text + text[last + 1:]
    return text + solid_text


_BLANK_VMF = """\
versioninfo
{{
\t"editorversion" "400"
\t"editorbuild" "8870"
\t"mapversion" "1"
\t"formatversion" "100"
\t"prefab" "0"
}}
visgroups
{{
}}
viewsettings
{{
\t"bSnapToGrid" "1"
\t"bShowGrid" "1"
\t"bShowLogicalGrid" "0"
\t"nGridSpacing" "64"
\t"bShow3DGrid" "0"
}}
world
{{
\t"id" "1"
\t"mapversion" "1"
\t"classname" "worldspawn"
\t"skyname" "{skyname}"
\t"startdark" "0"
}}
"""

# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def vmf_audit() -> str:
    """List all richbot_spawn_* info_target entities and their origins/angles."""
    text = _read()
    found = {}
    for block in re.finditer(r'^entity\s*\{([^{}]*)\}', text, re.MULTILINE | re.DOTALL):
        body = block.group(1)
        name_m = re.search(r'"targetname"\s+"richbot_spawn_(\w+)"', body)
        origin_m = re.search(r'"origin"\s+"([^"]+)"', body)
        angles_m = re.search(r'"angles"\s+"([^"]+)"', body)
        if name_m:
            found[name_m.group(1)] = {
                "origin": origin_m.group(1) if origin_m else "?",
                "angles": angles_m.group(1) if angles_m else "?",
            }

    bots = ["gerry","kyle","dale","ruth","maria","vincent","tex","rosencrantz","guildenstern"]
    lines = []
    for b in bots:
        if b in found:
            lines.append(f"OK       richbot_spawn_{b:<14} origin={found[b]['origin']}  angles={found[b]['angles']}")
        else:
            lines.append(f"MISSING  richbot_spawn_{b}")
    missing = [b for b in bots if b not in found]
    if missing:
        lines.append(f"\nMissing: {', '.join(missing)}")
    else:
        lines.append("\nAll present.")
    return "\n".join(lines)


@mcp.tool()
def vmf_get_entities(classname: str = "", name_pattern: str = "") -> str:
    """
    Query entities from the VMF.
    classname: filter by entity class (e.g. 'info_target', 'prop_door_rotating')
    name_pattern: filter by targetname substring (e.g. 'apt1', 'richbot')
    Returns up to 50 matches with their key properties.
    """
    text = _read()
    entities = _parse_entities(text)
    results = []
    for e in entities:
        if classname and e.get("classname", "") != classname:
            continue
        if name_pattern and name_pattern.lower() not in e.get("targetname", "").lower():
            continue
        info = {k: v for k, v in e.items() if not k.startswith("_")}
        results.append(str(info))
    if not results:
        return "No entities matched."
    return f"{len(results)} match(es):\n" + "\n".join(results[:50])


@mcp.tool()
def vmf_set_origin(targetname: str, origin: str, angles: str = "") -> str:
    """
    Move an entity by targetname. origin format: 'X Y Z'. angles optional: 'P Y R'.
    Example: vmf_set_origin('richbot_spawn_rosencrantz', '100 1619 -38')
    """
    text = _read()
    pattern = re.compile(
        r'(entity\s*\{[^{}]*"targetname"\s+"' + re.escape(targetname) + r'"[^{}]*\})',
        re.DOTALL
    )
    match = pattern.search(text)
    if not match:
        return f"ERROR: entity '{targetname}' not found."

    block = match.group(1)
    new_block = re.sub(r'"origin"\s+"[^"]*"', f'"origin" "{origin}"', block)
    if angles:
        new_block = re.sub(r'"angles"\s+"[^"]*"', f'"angles" "{angles}"', new_block)

    new_text = text[:match.start()] + new_block + text[match.end():]
    _write(new_text)
    return f"Moved '{targetname}' to {origin}" + (f" angles={angles}" if angles else "")


@mcp.tool()
def vmf_add_entity(classname: str, targetname: str, origin: str, angles: str = "0 0 0", extra_props: str = "") -> str:
    """
    Add a new entity to the VMF.
    extra_props: optional additional key=value pairs, semicolon-separated. e.g. 'model=models/foo.mdl;spawnflags=1'
    """
    text = _read()
    eid = _max_id(text) + 1
    props = {"classname": classname, "targetname": targetname, "origin": origin, "angles": angles}
    if extra_props:
        for pair in extra_props.split(";"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                props[k.strip()] = v.strip()

    block = _entity_block(props, eid)
    new_text = text.rstrip() + "\n" + block
    _write(new_text)
    return f"Added {classname} '{targetname}' at {origin} (id={eid})"


@mcp.tool()
def vmf_remove_entity(targetname: str) -> str:
    """Remove an entity by targetname. Creates a backup first."""
    text = _read()
    pattern = re.compile(
        r'entity\s*\{[^{}]*"targetname"\s+"' + re.escape(targetname) + r'"[^{}]*\}\n?',
        re.DOTALL
    )
    match = pattern.search(text)
    if not match:
        return f"ERROR: entity '{targetname}' not found."
    new_text = text[:match.start()] + text[match.end():]
    _write(new_text)
    return f"Removed entity '{targetname}'."


@mcp.tool()
def vmf_add_brush(
    x1: int, y1: int, z1: int,
    x2: int, y2: int, z2: int,
    material: str = "CONCRETE/CONCRETEFLOOR008A",
    nodraw_hidden: bool = True,
) -> str:
    """
    Add a single axis-aligned box brush to the world.
    (x1,y1,z1) is the min corner, (x2,y2,z2) is the max corner (Source units).
    material: applied to all 6 faces unless nodraw_hidden=True, in which case
              the 5 non-top faces use TOOLS/TOOLSNODRAW (good for floor slabs).
    Example: vmf_add_brush(0, 0, -16, 512, 512, 0, 'CONCRETE/CONCRETEFLOOR008A')
    """
    text = _read()
    bid = _max_id(text) + 1
    sid_start = bid + 1

    face_mats = None
    if nodraw_hidden:
        face_mats = {
            "bottom": "TOOLS/TOOLSNODRAW",
            "x-": "TOOLS/TOOLSNODRAW",
            "x+": "TOOLS/TOOLSNODRAW",
            "y-": "TOOLS/TOOLSNODRAW",
            "y+": "TOOLS/TOOLSNODRAW",
        }

    solid, _ = _box_solid(x1, y1, z1, x2, y2, z2, material, bid, sid_start, face_mats)
    new_text = _insert_into_world(text, solid)
    _write(new_text)
    return f"Added brush id={bid} [{x1},{y1},{z1}]→[{x2},{y2},{z2}] material={material}"


@mcp.tool()
def vmf_add_room(
    cx: int, cy: int, cz: int,
    width: int, depth: int, height: int,
    wall_material: str = "CONCRETE/CONCRETEWALL052A",
    floor_material: str = "CONCRETE/CONCRETEFLOOR008A",
    ceiling_material: str = "TOOLS/TOOLSNODRAW",
    thickness: int = 16,
    open_sides: str = "",
) -> str:
    """
    Add a hollow room (up to 6 brush slabs) to the world.
    open_sides: comma-separated list of wall sides to OMIT, enabling connections.
                Values: '-X', '+X', '-Y', '+Y'. Floor and ceiling are always added.
                Example: open_sides='+Y' leaves the +Y wall open for a hallway.
    The room interior spans from (cx-width/2, cy-depth/2, cz) to
    (cx+width/2, cy+depth/2, cz+height). All dimensions in Source units.
    thickness: wall/floor/ceiling slab thickness (default 16).
    """
    text = _read()
    bid = _max_id(text) + 1
    sid = bid + 1

    hw, hd = width // 2, depth // 2
    ix1, ix2 = cx - hw, cx + hw
    iy1, iy2 = cy - hd, cy + hd
    iz1, iz2 = cz, cz + height
    t = thickness

    skip = {s.strip().lower() for s in open_sides.split(",") if s.strip()}

    # (label_key, x1, y1, z1, x2, y2, z2, face_mats)
    slabs = [
        ("floor",  ix1,     iy1,     iz1 - t, ix2,     iy2,     iz1,
         {"top": floor_material, "bottom": "TOOLS/TOOLSNODRAW",
          "x-": "TOOLS/TOOLSNODRAW", "x+": "TOOLS/TOOLSNODRAW",
          "y-": "TOOLS/TOOLSNODRAW", "y+": "TOOLS/TOOLSNODRAW"}),
        ("ceiling", ix1,    iy1,     iz2,     ix2,     iy2,     iz2 + t,
         {"top": "TOOLS/TOOLSNODRAW", "bottom": ceiling_material,
          "x-": "TOOLS/TOOLSNODRAW", "x+": "TOOLS/TOOLSNODRAW",
          "y-": "TOOLS/TOOLSNODRAW", "y+": "TOOLS/TOOLSNODRAW"}),
        ("-x",  ix1 - t, iy1,     iz1,     ix1,     iy2,     iz2,     None),
        ("+x",  ix2,     iy1,     iz1,     ix2 + t, iy2,     iz2,     None),
        ("-y",  ix1 - t, iy1 - t, iz1,     ix2 + t, iy1,     iz2,     None),
        ("+y",  ix1 - t, iy2,     iz1,     ix2 + t, iy2 + t, iz2,     None),
    ]

    all_solids = ""
    labels = []
    for entry in slabs:
        key = entry[0]
        if key in skip:
            labels.append(f"  {key}: SKIPPED (open_sides)")
            continue
        if len(entry) == 8:
            _, x1s, y1s, z1s, x2s, y2s, z2s, face_mats = entry
        else:
            _, x1s, y1s, z1s, x2s, y2s, z2s = entry
            face_mats = None
        solid, sid = _box_solid(x1s, y1s, z1s, x2s, y2s, z2s,
                                wall_material, bid, sid, face_mats)
        all_solids += solid
        labels.append(f"  {key}: id={bid} [{x1s},{y1s},{z1s}]→[{x2s},{y2s},{z2s}]")
        bid = sid
        sid = bid + 1

    new_text = _insert_into_world(text, all_solids)
    _write(new_text)
    open_note = f" (open: {open_sides})" if open_sides else ""
    return (
        f"Added room {width}×{depth}×{height}u centered at ({cx},{cy}) floor z={cz}{open_note}\n"
        + "\n".join(labels)
    )


@mcp.tool()
def vmf_new_map(
    skyname: str = "sky_day02_04",
    starter_room_size: int = 512,
    starter_room_height: int = 256,
) -> str:
    """
    Scaffold a fresh VMF from scratch (overwrites current file, backup created).
    starter_room_size: XY interior dimension of the starter sealed room (0 = no room).
    Rosencrantz and Guildenstern are always placed in the center, facing each other.
    After this, use vmf_add_brush / vmf_add_room / vmf_add_entity to build the map,
    then vmf_compile to compile and deploy.
    """
    blank = _BLANK_VMF.format(skyname=skyname)
    _write(blank, backup=True)

    log = []
    if starter_room_size > 0:
        log.append(vmf_add_room(
            cx=0, cy=0, cz=0,
            width=starter_room_size,
            depth=starter_room_size,
            height=starter_room_height,
            wall_material="CONCRETE/CONCRETEWALL052A",
            floor_material="CONCRETE/CONCRETEFLOOR008A",
            ceiling_material="TOOLS/TOOLSNODRAW",
        ))
    else:
        log.append(f"New blank VMF created (skyname={skyname}).")

    # Rosencrantz and Guildenstern are always present — they know this.
    spawn_z = 0  # floor level
    offset = min(60, starter_room_size // 8) if starter_room_size > 0 else 60
    log.append(vmf_add_entity("info_target", "richbot_spawn_rosencrantz",
                               f"{offset} 0 {spawn_z}", angles="0 270 0"))
    log.append(vmf_add_entity("info_target", "richbot_spawn_guildenstern",
                               f"-{offset} 0 {spawn_z}", angles="0 90 0"))

    return "\n".join(log)


@mcp.tool()
def vmf_compile(fast: bool = True, final: bool = False) -> str:
    """
    Compile the VMF (vbsp → vvis → vrad) and copy BSP to srcds + GMod client.
    fast=True for iteration, final=True for high-quality lighting.
    """
    map_base = str(VMF_PATH.with_suffix(""))
    game = str(GMOD_GAME)

    steps = [
        ([str(GMOD_BIN / "vbsp.exe"), "-game", game, map_base], "vbsp"),
        ([str(GMOD_BIN / "vvis.exe"), "-game", game] + (["-fast"] if fast else []) + [map_base], "vvis"),
        ([str(GMOD_BIN / "vrad.exe"), "-game", game, "-hdr", "-both", "-bounce", "100"]
         + (["-fast"] if fast and not final else [])
         + (["-final"] if final else [])
         + [map_base], "vrad"),
    ]

    log = []
    for cmd, label in steps:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            out = (result.stdout + result.stderr)[-2000:]
            return f"ERROR: {label} failed (exit {result.returncode})\n{out}"
        log.append(f"{label}: OK")

    bsp_src = VMF_PATH.with_suffix(".bsp")
    if bsp_src.exists():
        for dest in [BSP_DEST, BSP_DEST_CLIENT]:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bsp_src, dest)
        log.append(f"BSP copied to server + client.")
    else:
        log.append("WARNING: BSP not found after compile.")

    return "\n".join(log)


if __name__ == "__main__":
    mcp.run()
