import shutil
vmf_path = 'rp_richland26.vmf'
shutil.copy(vmf_path, vmf_path + '.bak_before_watervmt2')
text = open(vmf_path, encoding='utf-8', errors='replace').read()
old = '"material" "DEV/DEV_WATER2_CHEAP"'
new = '"material" "MAPS/rp_richland26/POOL_WATER"'
count = text.count(old)
text = text.replace(old, new)
open(vmf_path, 'w', encoding='utf-8').write(text)
print(f'Replaced {count} face(s): {old} -> {new}')
