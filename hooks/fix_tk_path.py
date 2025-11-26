import os
import sys

def fix_tk_path():
    # Path inside PyInstaller's temp folder
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
        tcl_path = os.path.join(base, "tcl", "tcl8.6")
        tk_path  = os.path.join(base, "tcl", "tk8.6")

        os.environ["TCL_LIBRARY"] = tcl_path
        os.environ["TK_LIBRARY"] = tk_path

fix_tk_path()
