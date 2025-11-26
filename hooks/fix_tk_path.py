# hooks/fix_tk_path.py
import os
import sys

if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    base_path = sys._MEIPASS
    tcl_path = os.path.join(base_path, 'tcl8.6')
    tk_path  = os.path.join(base_path, 'tk8.6')

    if os.path.isdir(tcl_path):
        os.environ['TCL_LIBRARY'] = tcl_path
    if os.path.isdir(tk_path):
        os.environ['TK_LIBRARY'] = tk_path