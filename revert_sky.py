import shutil
vmf_path = 'rp_richland26.vmf'
shutil.copy(vmf_path, vmf_path + '.bak_before_revert_sky')
text = open(vmf_path, encoding='utf-8', errors='replace').read()
text = text.replace('"skyname" "sky_day01_01"', '"skyname" "sky_day02_04"')
open(vmf_path, 'w', encoding='utf-8').write(text)
print('Reverted sky to sky_day02_04')
