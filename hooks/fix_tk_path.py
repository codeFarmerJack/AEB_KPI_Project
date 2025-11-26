# hooks/fix_tk_path.py
# Works with PyInstaller 5.x / 6.x onedir builds (2023–2025)

import os
import sys

if getattr(sys, 'frozen', False):
    # PyInstaller onedir: everything is under the folder that contains the .exe
    exe_dir = os.path.dirname(sys.executable)

    # Try the two most common locations PyInstaller uses in 2023–2025
    candidates = [
        os.path.join(exe_dir, "tcl8.6"),           # you put them at root level
        os.path.join(exe_dir, "_internal", "tcl8.6"),
        os.path.join(exe_dir, "_internal", "tcl", "tcl8.6"),
    ]

    for tcl_candidate in candidates:
        if os.path.isdir(tcl_candidate):
            os.environ["TCL_LIBRARY"] = tcl_candidate
            # Also set TK_LIBRARY to the sibling folder
            tk_candidate = tcl_candidate.replace("tcl8.6", "tk8.6").replace("tcl\\tcl8.6", "tk\\tk8.6")
            if os.path.isdir(tk_candidate):
                os.environ["TK_LIBRARY"] = tk_candidate
            break

    # Optional: print for debugging (remove later)
    # print("TCL_LIBRARY =", os.environ.get("TCL_LIBRARY"))
    # print("TK_LIBRARY  =", os.environ.get("TK_LIBRARY"))