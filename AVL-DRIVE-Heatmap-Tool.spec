# -*- mode: python ; coding: utf-8 -*-
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, copy_metadata

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

# Copy source files into _internal — loaded at runtime via bundle_loader (not PYZ).
APP_SOURCE_FILES = [
    "app.py",
    "config.py",
    "bundle_loader.py",
    "heatmap_engine.py",
    "evaluation_engine.py",
    "heatmap_excel_export.py",
    "operation_modes.json",
]
datas = [(name, ".") for name in APP_SOURCE_FILES]

binaries = []
# Do NOT list local app modules in hiddenimports — that freezes stale bytecode in PYZ.
hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "openpyxl",
    "pandas",
    "matplotlib",
    "PIL",
    "plotly",
    "seaborn",
]

for pkg in ("streamlit", "pandas", "openpyxl", "matplotlib", "plotly", "seaborn", "Pillow"):
    datas += copy_metadata(pkg)

tmp_ret = collect_all("streamlit")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]


def _bundle_tcl_tk_data():
    """PyInstaller's tkinter runtime hook expects _tcl_data / _tk_data in _MEIPASS."""
    if sys.platform != "win32":
        return []
    bundled = []
    tcl_candidates = [
        os.path.join(sys.base_prefix, "tcl", "tcl8.6"),
        os.path.join(sys.base_prefix, "lib", "tcl8.6"),
    ]
    tk_candidates = [
        os.path.join(sys.base_prefix, "tcl", "tk8.6"),
        os.path.join(sys.base_prefix, "lib", "tk8.6"),
    ]
    for path in tcl_candidates:
        if os.path.isdir(path):
            bundled.append((path, "_tcl_data"))
            break
    for path in tk_candidates:
        if os.path.isdir(path):
            bundled.append((path, "_tk_data"))
            break
    return bundled


datas += _bundle_tcl_tk_data()

if sys.platform == "win32":
    py_dll = f"python{sys.version_info.major}{sys.version_info.minor}.dll"
    for candidate in (
        os.path.join(sys.base_prefix, py_dll),
        os.path.join(sys.base_prefix, "DLLs", py_dll),
    ):
        if os.path.isfile(candidate):
            binaries.append((candidate, "."))

    for pattern in ("vcruntime*.dll", "python*.dll", "msvcp*.dll"):
        for dll_path in glob.glob(os.path.join(sys.base_prefix, pattern)):
            binaries.append((dll_path, "."))

    dlls_dir = os.path.join(sys.base_prefix, "DLLs")
    if os.path.isdir(dlls_dir):
        for dll_path in glob.glob(os.path.join(dlls_dir, "*.dll")):
            binaries.append((dll_path, "DLLs"))

a = Analysis(
    ["launcher.py"],
    pathex=[SPEC_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "config",
        "heatmap_engine",
        "evaluation_engine",
        "heatmap_excel_export",
        "app",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends._backend_tk",
        "PIL.ImageTk",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AVL-DRIVE-Heatmap-Tool",
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
    name="AVL-DRIVE-Heatmap-Tool",
)
