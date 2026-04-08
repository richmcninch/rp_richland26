"""
Replace dev/dev_water2_cheap material on brush faces with maps/rp_richland26/pool_water.
pool_water.vmt already has $abovewater "1" and all correct water parameters.
"""
import re, shutil

vmf_path = 'rp_richland26.vmf'
shutil.copy(vmf_path, vmf_path + '.bak_before_watervmt')
text = open(vmf_path, encoding='utf-8', errors='replace').read()

old_mat = 'dev/dev_water2_cheap'
new_mat = 'maps/rp_richland26/pool_water'

count = text.count(f'"material" "{old_mat}"')
text = text.replace(f'"material" "{old_mat}"', f'"material" "{new_mat}"')

open(vmf_path, 'w', encoding='utf-8').write(text)
print(f'Replaced {count} face(s): {old_mat} -> {new_mat}')
