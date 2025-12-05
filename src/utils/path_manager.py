import os
import sys
from pathlib import Path

def get_src_root() -> Path:
    """
    Return the absolute path to the 'src/' directory.
    Works in:
        - normal Python execution
        - VSCode
        - PyInstaller bundle (onefile or onedir)
        - ANY working directory
    """
    # PyInstaller (_MEIPASS contains packaged src/)
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    # Normal: this file is in src/utils/
    return Path(__file__).resolve().parents[1]


def get_config_dir() -> Path:
    """Return path to src/config/"""
    return get_src_root() / "config"


def get_resource(path_relative_to_src: str) -> Path:
    """
    Load ANY file relative to src/
    Example:
        get_resource("config/enum_definitions.yaml")
        get_resource("pipeline/templates/template.xlsx")
    """
    return get_src_root() / path_relative_to_src


def get_project_root() -> Path:
    """
    Returns the folder that contains 'src'.
    Example:
        project/
            src/
            rawdata/
            outputs/
    """
    return get_src_root().parent

def init_tkinter_for_bundle():
    """Ensure Tcl/Tk works inside PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        os.environ["TCL_LIBRARY"] = str(base / "tcl")
        os.environ["TK_LIBRARY"]  = str(base / "tk")

