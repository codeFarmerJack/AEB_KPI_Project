import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
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


def test_selecting_files_sets_active_folder_and_count(tmp_path):
    _get_app()

    folder_a = tmp_path / "folder_a"
    folder_a.mkdir()
    file_a = folder_a / "a.mf4"
    file_b = folder_a / "b.mf4"
    file_a.write_text("")
    file_b.write_text("")

    gui = KpiGui(tree_root=tmp_path)
    gui._set_selected_files([file_a, file_b])

    assert gui._selected_files() == [file_a.resolve(), file_b.resolve()]
    assert gui.mf4_folder == folder_a.resolve()
    assert gui.file_count.text() == "2 selected"
    assert gui.file_checks[file_a.resolve()].text() == "a.mf4"
    assert gui.file_checks[file_b.resolve()].text() == "b.mf4"


def test_selected_file_rows_can_be_unchecked(tmp_path):
    _get_app()

    folder = tmp_path / "folder"
    folder.mkdir()
    file_a = folder / "a.mf4"
    file_b = folder / "b.mf4"
    file_a.write_text("")
    file_b.write_text("")

    gui = KpiGui(tree_root=tmp_path)
    gui._set_selected_files([file_a, file_b])
    gui.file_checks[file_b.resolve()].setChecked(False)

    assert gui._selected_files() == [file_a.resolve()]
    assert gui.file_count.text() == "1 selected"


def test_selected_file_pane_height_scales_with_visible_rows(tmp_path):
    _get_app()

    folder = tmp_path / "folder"
    folder.mkdir()
    files = []
    for idx in range(8):
        path = folder / f"{idx}.mf4"
        path.write_text("")
        files.append(path)

    gui = KpiGui(tree_root=tmp_path)
    initial_height = gui.file_scroll.maximumHeight()

    gui._set_selected_files(files[:3])
    three_file_height = gui.file_scroll.maximumHeight()

    gui._set_selected_files(files)
    capped_height = gui.file_scroll.maximumHeight()

    assert three_file_height > initial_height
    assert capped_height > three_file_height
    assert capped_height == 16 + 5 * 32


def test_rejects_files_from_multiple_folders(tmp_path):
    _get_app()

    folder_a = tmp_path / "folder_a"
    folder_b = tmp_path / "folder_b"
    folder_a.mkdir()
    folder_b.mkdir()
    file_a = folder_a / "a.mf4"
    file_b = folder_b / "b.mf4"
    file_a.write_text("")
    file_b.write_text("")

    gui = KpiGui(tree_root=tmp_path)
    gui._set_selected_files([file_a, file_b])

    assert gui._selected_files() == []
    assert gui.file_count.text() == "0 selected"


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
