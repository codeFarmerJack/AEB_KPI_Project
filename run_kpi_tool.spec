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

# Windows stores Tcl/Tk in <python>/tcl/
# macOS/Linux store Tcl/Tk in <python>/Lib/tkinter/tcl/
if sys.platform.startswith("win"):
    tcl_base = os.path.join(sys.base_prefix, "tcl")
else:
    tcl_base = os.path.join(os.path.dirname(tkinter.__file__), "tcl")

# Only include directories that actually exist
if os.path.isdir(tcl_base):
    # For your Windows Python312, these will be: tcl8.6 and tk8.6
    for name in ("tcl8.6", "tk8.6"):
        full_path = os.path.join(tcl_base, name)
        if os.path.isdir(full_path):
            datas.append((full_path, os.path.join("tcl", name)))

# Include tkinter runtime files
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
