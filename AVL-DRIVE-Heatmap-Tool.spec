# -*- mode: python ; coding: utf-8 -*-
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

# Local application modules — must be listed here so PyInstaller freezes the
# current source into the bundle (not a stale copy from elsewhere on sys.path).
APP_MODULES = [
    'config',
    'heatmap_engine',
    'evaluation_engine',
    'heatmap_excel_export',
]

# Streamlit executes app.py by file path, so keep it as a data file in _MEIPASS.
datas = [('app.py', '.')]

binaries = []
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner',
    'streamlit.runtime.scriptrunner.magic_funcs',
    'openpyxl',
    'pandas',
    'matplotlib',
    'PIL',
    'plotly',
    'seaborn',
] + APP_MODULES

for pkg in ('streamlit', 'pandas', 'openpyxl', 'matplotlib', 'plotly', 'seaborn', 'Pillow'):
    datas += copy_metadata(pkg)

tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Explicitly bundle Python runtime DLLs (fixes "Failed to load Python DLL" on Windows).
# UPX compression is disabled below because it can also break DLL loading.
if sys.platform == 'win32':
    py_dll = f'python{sys.version_info.major}{sys.version_info.minor}.dll'
    for candidate in (
        os.path.join(sys.base_prefix, py_dll),
        os.path.join(sys.base_prefix, 'DLLs', py_dll),
    ):
        if os.path.isfile(candidate):
            binaries.append((candidate, '.'))

    for pattern in ('vcruntime*.dll', 'python*.dll', 'msvcp*.dll'):
        for dll_path in glob.glob(os.path.join(sys.base_prefix, pattern)):
            binaries.append((dll_path, '.'))

    dlls_dir = os.path.join(sys.base_prefix, 'DLLs')
    if os.path.isdir(dlls_dir):
        for dll_path in glob.glob(os.path.join(dlls_dir, '*.dll')):
            binaries.append((dll_path, 'DLLs'))

a = Analysis(
    ['launcher.py'],
    pathex=[SPEC_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AVL-DRIVE-Heatmap-Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AVL-DRIVE-Heatmap-Tool',
)
