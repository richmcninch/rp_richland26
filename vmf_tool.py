"""
vmf_tool.py — RichBots map toolbelt for rp_richland26

Usage:
  python vmf_tool.py audit              # check bot spawn markers in VMF
  python vmf_tool.py inject [--apply]   # add missing spawn markers (dry run by default)
  python vmf_tool.py compile [--fast] [--final]  # run vbsp/vvis/vrad + copy BSP to srcds
  python vmf_tool.py deploy [--fast]    # compile + changelevel on running srcds via RCON
"""
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

VMF_PATH    = Path(__file__).parent / "rp_richland26.vmf"
MAP_BASE    = str(VMF_PATH.with_suffix(""))          # no extension

GMOD_BIN    = Path(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64")
GMOD_GAME   = Path(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod")
BSP_DEST       = Path(r"F:\richbots\server\garrysmod\maps\rp_richland26.bsp")
BSP_DEST_CLIENT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod\maps\rp_richland26.bsp")

BOT_IDS = [
    "gerry", "kyle", "dale", "ruth", "maria",
    "vincent", "tex", "rosencrantz", "guildenstern",
]

# Positions derived from map geometry (kitchen light fixtures + confirmed Gerry position).
# All at floor Z=24 to match Gerry's confirmed placement.
SPAWN_POSITIONS: dict[str, str | None] = {
    "gerry":        "-793 82 24",    # apt 1 — confirmed by user
    "kyle":         "-793 -82 24",   # apt 2 — mirror of apt 1
    "dale":         "-581 82 24",    # apt 3 — derived from lights_apt3_model
    "ruth":         "-581 -82 24",   # apt 4 — derived from lights_apt4_model
    "maria":        "581 82 24",     # apt 5 — derived from lights_apt5_model
    "vincent":      "581 -82 24",    # apt 6 — derived from apt6_kitchenbomb + lights_apt6_model
    "tex":          "793 -82 24",    # apt 8 — derived from lights_apt8_model
    "rosencrantz":  "100 1619 -38",  # front office — derived from office floor entities
    "guildenstern": "-100 1619 -38", # front office — beside rosencrantz
}

# RCON settings for 'deploy' (reads from env if not set here)
import os
RCON_HOST = os.environ.get("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.environ.get("RCON_PORT", "27015"))
RCON_PASS = os.environ.get("RCON_PASSWORD", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_vmf():
    from srctools.vmf import VMF
    if not VMF_PATH.exists():
        print(f"ERROR: VMF not found at {VMF_PATH}", file=sys.stderr)
        sys.exit(1)
    return VMF.parse(VMF_PATH)


def _get_existing_ids(vmf) -> dict[str, dict]:
    found = {}
    for ent in vmf.entities:
        name = ent.get("targetname", "")
        if ent.get("classname", "") == "info_target" and name.startswith("richbot_spawn_"):
            bot_id = name.removeprefix("richbot_spawn_")
            found[bot_id] = {
                "origin": ent.get("origin", "0 0 0"),
                "angles": ent.get("angles", "0 0 0"),
            }
    return found


def _run(cmd: list[str], label: str) -> int:
    print(f"\n[{label}]", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    return result.returncode

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_audit():
    if not VMF_PATH.exists():
        print(f"ERROR: VMF not found at {VMF_PATH}", file=sys.stderr)
        sys.exit(1)

    import re
    text = VMF_PATH.read_text(encoding="utf-8", errors="replace")

    # Extract info_target blocks with richbot_spawn_ names
    found = {}
    for block in re.finditer(r'entity\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', text, re.DOTALL):
        body = block.group(1)
        cls_m = re.search(r'"classname"\s+"(\w+)"', body)
        name_m = re.search(r'"targetname"\s+"richbot_spawn_(\w+)"', body)
        origin_m = re.search(r'"origin"\s+"([^"]+)"', body)
        angles_m = re.search(r'"angles"\s+"([^"]+)"', body)
        if cls_m and cls_m.group(1) == "info_target" and name_m:
            found[name_m.group(1)] = {
                "origin": origin_m.group(1) if origin_m else "?",
                "angles": angles_m.group(1) if angles_m else "?",
            }

    print(f"\n{'ID':<16} {'STATUS':<10} {'ORIGIN':<30} ANGLES")
    print("-" * 72)
    for bot_id in BOT_IDS:
        if bot_id in found:
            o = found[bot_id]["origin"]
            a = found[bot_id]["angles"]
            print(f"{bot_id:<16} {'OK':<10} {o:<30} {a}")
        else:
            print(f"{bot_id:<16} {'MISSING':<10}")

    extra = set(found.keys()) - set(BOT_IDS)
    if extra:
        print(f"\nExtra markers (not in config): {', '.join(sorted(extra))}")

    missing = [b for b in BOT_IDS if b not in found]
    if missing:
        print(f"\nMissing ({len(missing)}): {', '.join(missing)}")
        print("Run: python vmf_tool.py inject [--apply]")
    else:
        print("\nAll bot spawn markers present.")


def _entity_block(bot_id: str, origin: str, eid: int) -> str:
    """Build a raw VMF info_target entity block for text injection."""
    return (
        f'entity\n'
        f'{{\n'
        f'\t"id" "{eid}"\n'
        f'\t"classname" "info_target"\n'
        f'\t"targetname" "richbot_spawn_{bot_id}"\n'
        f'\t"origin" "{origin}"\n'
        f'\t"angles" "0 0 0"\n'
        f'}}\n'
    )


def _get_existing_ids_raw(text: str) -> set[str]:
    """Extract richbot_spawn_* targetnames from raw VMF text."""
    import re
    return set(re.findall(r'"targetname"\s+"richbot_spawn_(\w+)"', text))


def _max_entity_id(text: str) -> int:
    import re
    ids = [int(x) for x in re.findall(r'"id"\s+"(\d+)"', text)]
    return max(ids) if ids else 1


def cmd_inject(apply: bool):
    if not VMF_PATH.exists():
        print(f"ERROR: VMF not found at {VMF_PATH}", file=sys.stderr)
        sys.exit(1)

    text = VMF_PATH.read_text(encoding="utf-8", errors="replace")
    existing = _get_existing_ids_raw(text)
    to_add = [b for b in BOT_IDS if b not in existing]

    if not to_add:
        print("All bot spawn markers already present. Nothing to do.")
        return

    print(f"\n{'[DRY RUN] ' if not apply else ''}Will add {len(to_add)} marker(s): {', '.join(to_add)}")
    for bot_id in to_add:
        origin = SPAWN_POSITIONS.get(bot_id) or "0 0 128"
        print(f"  + richbot_spawn_{bot_id} @ {origin}")

    if not apply:
        print("\nPass --apply to write changes.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = VMF_PATH.with_name(f"rp_richland26.vmf.bak_{ts}")
    shutil.copy2(VMF_PATH, backup)
    print(f"\nBackup: {backup.name}")

    next_id = _max_entity_id(text) + 1
    blocks = ""
    for bot_id in to_add:
        origin = SPAWN_POSITIONS.get(bot_id) or "0 0 128"
        blocks += _entity_block(bot_id, origin, next_id)
        next_id += 1

    # Always append after the file — never modify existing braces.
    # VMF is a flat sequence of top-level blocks; simply adding entity blocks
    # at the end is always valid regardless of what the last block is.
    new_text = text.rstrip() + "\n" + blocks

    VMF_PATH.write_text(new_text, encoding="utf-8")
    print(f"Saved. {len(to_add)} marker(s) added (text injection, geometry untouched).")
    print("Open Hammer++ and verify/reposition each marker.")


def cmd_compile(fast: bool, final: bool):
    print("=== rp_richland26 compile ===")
    if not VMF_PATH.exists():
        print(f"ERROR: VMF not found: {VMF_PATH}", file=sys.stderr)
        sys.exit(1)

    vbsp = str(GMOD_BIN / "vbsp.exe")
    vvis = str(GMOD_BIN / "vvis.exe")
    vrad = str(GMOD_BIN / "vrad.exe")
    game = str(GMOD_GAME)

    rc = _run([vbsp, "-game", game, MAP_BASE], "1/3 vbsp")
    if rc != 0:
        print(f"ERROR: vbsp failed (exit {rc})", file=sys.stderr); sys.exit(rc)

    vis_args = [vvis, "-game", game]
    if fast:
        vis_args.append("-fast")
    rc = _run(vis_args + [MAP_BASE], "2/3 vvis")
    if rc != 0:
        print(f"ERROR: vvis failed (exit {rc})", file=sys.stderr); sys.exit(rc)

    rad_args = [vrad, "-game", game, "-bounce", "100"]
    if final:
        rad_args.append("-final")
    elif fast:
        rad_args.append("-fast")
    rc = _run(rad_args + [MAP_BASE], "3/3 vrad")
    if rc != 0:
        print(f"ERROR: vrad failed (exit {rc})", file=sys.stderr); sys.exit(rc)

    bsp_src = VMF_PATH.with_suffix(".bsp")
    if bsp_src.exists():
        for dest in [BSP_DEST, BSP_DEST_CLIENT]:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bsp_src, dest)
            print(f"\nBSP copied -> {dest}")
        print("Load with: changelevel rp_richland26")
    else:
        print(f"WARNING: BSP not found at {bsp_src}", file=sys.stderr)

    # Sync custom materials and models to server
    repo_root = VMF_PATH.parent
    srv_root = BSP_DEST.parent.parent  # server/garrysmod
    for asset_dir in ["materials", "models"]:
        src_dir = repo_root / asset_dir
        dst_dir = srv_root / asset_dir
        if src_dir.exists():
            shutil.copytree(str(src_dir), str(dst_dir), dirs_exist_ok=True)
            count = sum(1 for _ in src_dir.rglob("*") if _.is_file())
            print(f"Assets synced  -> {dst_dir}  ({count} files)")


def cmd_deploy(fast: bool):
    cmd_compile(fast=fast, final=False)

    if not RCON_PASS:
        print("\nRCON_PASSWORD not set — skipping changelevel.")
        print("Set it in F:\\richbots\\config\\.env.local and re-run, or run changelevel manually in srcds.")
        return

    try:
        from rcon.source import Client
        with Client(RCON_HOST, RCON_PORT, passwd=RCON_PASS) as client:
            resp = client.run("changelevel", "rp_richland26")
            print(f"\nRCON changelevel: {resp or 'OK'}")
    except ImportError:
        print("\nrcon package not installed. Run: pip install rcon")
        print("Then re-run: python vmf_tool.py deploy")
    except Exception as e:
        print(f"\nRCON failed: {e}", file=sys.stderr)

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "audit":
        cmd_audit()
    elif cmd == "inject":
        cmd_inject(apply="--apply" in args)
    elif cmd == "compile":
        cmd_compile(fast="--fast" in args, final="--final" in args)
    elif cmd == "deploy":
        cmd_deploy(fast="--fast" in args)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
