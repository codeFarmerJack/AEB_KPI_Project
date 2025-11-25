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
# These paths are correct for official python.org installers + Homebrew Python
# macOS ARM uses these exact library names
tcl_path = os.path.join(sys.base_prefix, "lib", "tcl8.6")
tk_path  = os.path.join(sys.base_prefix, "lib", "tk8.6")

# Add Tcl/Tk folders to bundle if they exist
if os.path.isdir(tcl_path) and os.path.isdir(tk_path):
    datas += [
        (tcl_path, "tcl"),
        (tk_path, "tk"),
    ]

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
