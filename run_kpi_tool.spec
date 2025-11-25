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
    (os.path.join(project_root, "AS_KPI.slx"), "."),
]


# ----------------------------------------------------------
# Add Tcl/Tk support (REQUIRED for Tkinter)
# ----------------------------------------------------------
# Auto-detect where tkinter stores Tcl/Tk (works on BOTH macOS + Windows)
tcl_dir = os.path.join(os.path.dirname(tkinter.__file__), "tcl")

for name in os.listdir(tcl_dir):
    full_path = os.path.join(tcl_dir, name)
    if os.path.isdir(full_path):
        datas.append((full_path, os.path.join("tcl", name)))

# Add extra tkinter resources
datas += collect_data_files("tkinter", include_py_files=True)


# Tkinter modules
hiddenimports = [
    "tkinter",
    "tkinter.filedialog",
    "tkinter._fix",
]


block_cipher = None


# ----------------------------------------------------------
# Build the analysis
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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


# ----------------------------------------------------------
# Platform-specific output
# ----------------------------------------------------------

if is_macos:
    # macOS .app bundle
    app = BUNDLE(
        EXE(
            pyz,
            a.scripts,
            a.binaries,
            a.zipfiles,
            a.datas,
            name='ADAS_KPI_Tool',
            console=True,
        ),
        name='ADAS_KPI_Tool.app',
    )

elif is_windows:
    # Windows .exe
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='ADAS_KPI_Tool',
        console=True,
    )
