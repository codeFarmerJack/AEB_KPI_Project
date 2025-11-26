import os, sys

# Only run inside PyInstaller
if hasattr(sys, "_MEIPASS"):
    tcl_path = os.path.join(sys._MEIPASS, "tcl", "tcl8.6")
    tk_path  = os.path.join(sys._MEIPASS, "tcl", "tk8.6")

    os.environ["TCL_LIBRARY"] = tcl_path
    os.environ["TK_LIBRARY"] = tk_path
