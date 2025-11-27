# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import matplotlib
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# -------------------------------
# Your project files
# -------------------------------
datas = [
    ('config', 'config'),
    ('pipeline', 'pipeline'),
    ('utils', 'utils'),
    # ('AS_KPI.slx', '.'),
]

datas += [(matplotlib.get_data_path(), "matplotlib/mpl-data")]

hiddenimports = [
    "matplotlib",
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.font_manager",

    "plotly",
    "plotly.graph_objs",
    "plotly.io._json",
    "plotly.io._renderers",
    "plotly.matplotlylib",
    "plotly.subplots",
    "plotly.utils._plotly_jsonencoder",

    "jsonschema",
]


# -------------------------------
# Windows: include Tcl/Tk correctly (flat dest—no _internal prefix)
# -------------------------------
if sys.platform.startswith('win'):
    # Find where Python installed tcl/tk
    tcl_src = os.path.join(sys.base_prefix, 'tcl', 'tcl8.6')
    tk_src  = os.path.join(sys.base_prefix, 'tcl', 'tk8.6')
    
    if os.path.exists(tcl_src):
        datas += [(tcl_src, 'tcl8.6')]  # Flat: PyInstaller puts in _internal automatically
    if os.path.exists(tk_src):
        datas += [(tk_src, 'tk8.6')]

# Collect all tkinter internal files
datas += collect_data_files('tkinter', include_py_files=True)

# -------------------------------
# Analysis (exclude the built-in rthook to avoid early failure)
# -------------------------------
a = Analysis(
    ['run_kpi_tool.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    runtime_hooks=['hooks/fix_tk_path.py'],
    excludes=['pyi_rth__tkinter'],  # ← CRUCIAL: Disable built-in hook
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ADAS_KPI_Tool',
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ADAS_KPI_Tool'
)

if sys.platform == "darwin":
    APP = BUNDLE(
        coll,
        name='ADAS_KPI_Tool.app',
        icon=None,
        bundle_identifier=None,
    )