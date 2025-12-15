# hooks/fix_tk_path.py
# Runs BEFORE any Tkinter code—fixes for PyInstaller 6.x+ onedir (2025)

import os
import sys

# Only in frozen bundle
if getattr(sys, 'frozen', False) and sys.platform.startswith('win'):
    # Onedir: base is the dist folder containing exe
    base_dir = os.path.dirname(sys.executable)
    
    # Exact path to bundled files (PyInstaller puts them here in 6.x+)
    tcl_dir = os.path.join(base_dir, '_internal', 'tcl8.6')
    tk_dir = os.path.join(base_dir, '_internal', 'tk8.6')
    
    # Set only if files exist
    if os.path.isdir(tcl_dir) and os.path.isfile(os.path.join(tcl_dir, 'init.tcl')):
        os.environ['TCL_LIBRARY'] = tcl_dir
        # print(f"[DEBUG] Set TCL_LIBRARY to: {tcl_dir}")
    
    if os.path.isdir(tk_dir) and os.path.isfile(os.path.join(tk_dir, 'tk.tcl')):
        os.environ['TK_LIBRARY'] = tk_dir
        # print(f"[DEBUG] Set TK_LIBRARY to: {tk_dir}")
    
    # Force prepend to Tcl's search paths (extra safety)
    if 'TCL_LIBRARY' in os.environ:
        os.environ['TCLLIBPATH'] = tcl_dir + os.pathsep + os.environ.get('TCLLIBPATH', '')
