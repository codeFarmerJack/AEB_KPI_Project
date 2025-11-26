# hooks/fix_tk_path.py
# 100% working fix for PyInstaller 6.x+ onedir builds (2024–2025)

import os
import sys

if getattr(sys, 'frozen', False):
    # In PyInstaller 6.x+ onedir mode → everything is under _internal
    base = os.path.dirname(sys.executable)
    tcl_dir = os.path.join(base, "_internal", "tcl8.6")
    tk_dir  = os.path.join(base, "_internal", "tk8.6")

    # Debug prints (you can keep them temporarily to confirm)
    # print("Looking for Tcl/Tk in:", base)
    # print("TCL_LIBRARY candidate:", tcl_dir)
    # print("TK_LIBRARY  candidate:", tk_dir)

    if os.path.isdir(tcl_dir) and os.path.isfile(os.path.join(tcl_dir, "init.tcl")):
        os.environ["TCL_LIBRARY"] = tcl_dir
        # print("TCL_LIBRARY set to:", tcl_dir)

    if os.path.isdir(tk_dir) and os.path.isfile(os.path.join(tk_dir, "tk.tcl")):
        os.environ["TK_LIBRARY"] = tk_dir
        # print("TK_LIBRARY set to:", tk_dir)