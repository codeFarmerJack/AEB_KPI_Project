# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import tkinter
from PyInstaller.utils.hooks import collect_data_files

project_root = os.getcwd()
is_macos = sys.platform == "darwin"
is_windows = sys.platform.startswith("win")

# ----------------------------------------------------------
# Include project folders
# ----------------------------------------------------------
datas = [
    (os.path.join(project_root, "config"), "config"),
    (os.path.join(project_root, "pipeline"), "pipeline"),
    (os.path.join(project_root, "utils"), "utils"),
#    (os.path.join(project_root, "AS_KPI.slx"), "."),
]

# ----------------------------------------------------------
# Force include Tcl/Tk for Windows
# ----------------------------------------------------------
if is_windows:
    python_root = sys.base_prefix
    tcl_source = os.path.join(python_root, "tcl")

    datas.append((os.path.join(tcl_source, "tcl8.6"), "tcl/tcl8.6"))
    datas.append((os.path.join(tcl_source, "tk8.6"), "tcl/tk8.6"))

# Tkinter assets
datas += collect_data_files("tkinter", include_py_files=True)

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
    hookspath=['hooks'],
    runtime_hooks=['hooks/fix_tk_path.py'],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='ADAS_KPI_Tool',
    console=True,
)

# ----------------------------------------------------------
# ONEDIR MODE (required for Windows Tkinter)
# ----------------------------------------------------------
if is_windows:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='ADAS_KPI_Tool'
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
