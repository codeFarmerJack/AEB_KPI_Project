# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
import matplotlib
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# -------------------------------------
# Project Structure
# -------------------------------------
ROOT = Path.cwd()
SRC  = ROOT / "src"

datas = [
    (str(SRC / "config"), "config"),
    (str(SRC / "pipeline"), "pipeline"),
    (str(SRC / "utils"), "utils"),
    (str(SRC / "viz"), "viz"),
    (str(SRC / "gui"), "gui"),
]

# Matplotlib assets
datas += [(matplotlib.get_data_path(), "matplotlib/mpl-data")]
datas += collect_data_files("pyecharts", include_py_files=True)

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

    # PySide6 modules for the GUI
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

hiddenimports += collect_submodules("pyecharts")

# Windows — include Tcl/Tk
if sys.platform.startswith('win'):
    tcl_src = os.path.join(sys.base_prefix, 'tcl', 'tcl8.6')
    tk_src  = os.path.join(sys.base_prefix, 'tcl', 'tk8.6')

    if os.path.exists(tcl_src):
        datas.append((tcl_src, 'tcl8.6'))
    if os.path.exists(tk_src):
        datas.append((tk_src, 'tk8.6'))

datas += collect_data_files("tkinter", include_py_files=True)

a = Analysis(
    ['src/run_kpi_tool.py'],     
    pathex=[str(ROOT), str(SRC)],  
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    runtime_hooks=['hooks/fix_tk_path.py'],
    excludes=['pyi_rth__tkinter'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
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
    name='ADAS_KPI_Tool'
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name='ADAS_KPI_Tool.app',
        icon=None,
        bundle_identifier=None,
    )
