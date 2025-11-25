# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# PyInstaller does NOT set __file__ inside .spec files
project_root = os.getcwd()

is_macos = sys.platform == "darwin"

# ----------------------------------------------------------
# Include project folders
# ----------------------------------------------------------
datas = [
    (os.path.join(project_root, "config"), "config"),
    (os.path.join(project_root, "pipeline"), "pipeline"),
    (os.path.join(project_root, "utils"), "utils"),
    (os.path.join(project_root, "AS_KPI.slx"), "."),
]

# ----------------------------------------------------------
# Add Tcl/Tk support (REQUIRED for Tkinter)
# ----------------------------------------------------------
import tkinter

# Tkinter stores its Tcl files inside its own package directory:
# <python>/Lib/tkinter/tcl/tcl8.6
tcl_dir = os.path.join(os.path.dirname(tkinter.__file__), "tcl")

for name in ("tcl8.6", "tk8.6"):
    full_path = os.path.join(tcl_dir, name)
    if os.path.isdir(full_path):
        datas.append((full_path, os.path.join("tcl", name)))

# Include other tkinter assets
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files("tkinter", include_py_files=True)


# Tkinter required modules
hiddenimports = [
    "tkinter",
    "tkinter.filedialog",
    "tkinter._fix",
]

block_cipher = None

# ----------------------------------------------------------
# Build
# ----------------------------------------------------------
a = Analysis(
    ['run_kpi_tool.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ----------------------------------------------------------
# Console EXE
# ----------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ADAS_KPI_Tool',
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

# ----------------------------------------------------------
# macOS .app bundle
# ----------------------------------------------------------
if is_macos:
    app = BUNDLE(
        exe,
        name='ADAS_KPI_Tool.app',
        icon=None,
    )
