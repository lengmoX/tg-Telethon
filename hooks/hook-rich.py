# PyInstaller hook for rich library
# This ensures all unicode data files are included

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files from rich (especially _unicode_data)
datas = collect_data_files('rich')

# Collect all submodules including dynamic ones
hiddenimports = collect_submodules('rich')
