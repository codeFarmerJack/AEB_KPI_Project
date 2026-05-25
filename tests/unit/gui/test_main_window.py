import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.gui.main_window import KpiGui


def _get_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_switching_to_a_different_folder_keeps_latest_checked_file(tmp_path):
    _get_app()

    folder_a = tmp_path / "folder_a"
    folder_b = tmp_path / "folder_b"
    folder_a.mkdir()
    folder_b.mkdir()
    file_a = folder_a / "a.mf4"
    file_b = folder_b / "b.mf4"
    file_a.write_text("")
    file_b.write_text("")

    gui = KpiGui()
    gui.tree_root = tmp_path
    gui.file_model.setRootPath(str(tmp_path))
    gui.file_tree.setRootIndex(gui.file_model.index(str(tmp_path)))

    idx_a = gui.file_model.index(str(file_a))
    idx_b = gui.file_model.index(str(file_b))

    assert gui.file_model.setData(idx_a, Qt.Checked, Qt.CheckStateRole)
    assert gui._selected_files() == [file_a]
    assert gui.mf4_folder == folder_a

    assert gui.file_model.setData(idx_b, Qt.Checked, Qt.CheckStateRole)

    assert gui._selected_files() == [file_b]
    assert gui.mf4_folder == folder_b
    assert gui.file_count.text() == "1 selected"


def test_gui_restores_last_active_mf4_folder(tmp_path):
    _get_app()

    folder = tmp_path / "remember_me"
    folder.mkdir()
    settings_path = tmp_path / "gui_settings.ini"

    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.clear()
    settings.sync()

    gui = KpiGui(settings=settings, tree_root=tmp_path)
    gui._set_active_folder(folder)
    gui.deleteLater()

    restored_settings = QSettings(str(settings_path), QSettings.IniFormat)
    restored_gui = KpiGui(settings=restored_settings, tree_root=tmp_path)

    assert restored_gui.mf4_folder == folder.resolve()


def test_gui_signal_source_selector_maps_motion_1(tmp_path):
    _get_app()

    settings = QSettings(str(tmp_path / "gui_settings.ini"), QSettings.IniFormat)
    settings.clear()
    settings.sync()

    gui = KpiGui(settings=settings, tree_root=tmp_path)
    gui.source_combo.setCurrentText("MOTION_1")

    assert gui._selected_signal_source() == "motion_1"

    restored_gui = KpiGui(settings=settings, tree_root=tmp_path)
    assert restored_gui.source_combo.currentText() == "MOTION_1"
