from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QDir, Signal, QEvent, QSettings
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QCheckBox,
    QFrame,
    QTreeView,
    QFileSystemModel,
    QAbstractItemView,
    QHeaderView,
    QStyledItemDelegate,
    QSplitter,
    QSpacerItem,
    QSizePolicy,
)

from src.gui.controllers.pipeline_runner import PipelineRunner
from src.utils.path_manager import get_config_dir


class FileTreeModel(QFileSystemModel):
    check_state_changed = Signal(str, int)

    @staticmethod
    def _state_value(state):
        return int(getattr(state, "value", state))

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checks = {}

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid() and self._is_mf4(index) and index.column() == 0:
            flags |= (
                Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
                | Qt.ItemIsEditable
            )
        return flags

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole and self._is_mf4(index) and index.column() == 0:
            path = self.filePath(index)
            return self._checks.get(path, Qt.Unchecked)
        return super().data(index, role)

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole and self._is_mf4(index) and index.column() == 0:
            path = self.filePath(index)
            state = Qt.Checked if value == Qt.Checked else Qt.Unchecked
            if self._checks.get(path) != state:
                self._checks[path] = state
                self.dataChanged.emit(index, index, [Qt.CheckStateRole])
                self.check_state_changed.emit(path, self._state_value(state))
            return True
        return super().setData(index, value, role)

    def checked_files(self):
        return [Path(p) for p, s in self._checks.items() if s == Qt.Checked]

    def clear_checks(self):
        changed = False
        for path, state in list(self._checks.items()):
            if state == Qt.Checked:
                self._checks[path] = Qt.Unchecked
                idx = self.index(path)
                if idx.isValid():
                    self.dataChanged.emit(idx, idx, [Qt.CheckStateRole])
                changed = True
        if changed:
            self.check_state_changed.emit("", self._state_value(Qt.Unchecked))

    def set_checked_paths(self, paths, checked=True):
        state = Qt.Checked if checked else Qt.Unchecked
        changed = False
        last_path = ""
        for path in paths:
            idx = self.index(str(path))
            if not idx.isValid():
                continue
            if self._checks.get(str(path)) != state:
                self._checks[str(path)] = state
                self.dataChanged.emit(idx, idx, [Qt.CheckStateRole])
                changed = True
                last_path = str(path)
        if changed:
            self.check_state_changed.emit(last_path, self._state_value(state))

    def clear_checks_outside_dir(self, folder: Path):
        folder = Path(folder).resolve()
        changed = False
        for path, state in list(self._checks.items()):
            if state != Qt.Checked:
                continue
            if Path(path).resolve().parent != folder:
                self._checks[path] = Qt.Unchecked
                idx = self.index(path)
                if idx.isValid():
                    self.dataChanged.emit(idx, idx, [Qt.CheckStateRole])
                changed = True
        if changed:
            self.check_state_changed.emit("", self._state_value(Qt.Unchecked))

    def _is_mf4(self, index):
        if not index.isValid() or self.isDir(index):
            return False
        return self.filePath(index).lower().endswith(".mf4")


class FileTreeDelegate(QStyledItemDelegate):
    def editorEvent(self, event, model, option, index):
        if (
            event.type() == QEvent.MouseButtonRelease
            and event.button() == Qt.LeftButton
            and index.isValid()
            and index.column() == 0
        ):
            path = model.filePath(index)
            if path.lower().endswith(".mf4") and not model.isDir(index):
                current = model.data(index, Qt.CheckStateRole)
                new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                model.setData(index, new_state, Qt.CheckStateRole)
                return True
        return super().editorEvent(event, model, option, index)


class KpiGui(QWidget):
    _SETTINGS_ORG = "JackWang401"
    _SETTINGS_APP = "ADAS_KPI_Extractor"
    _LAST_FOLDER_KEY = "gui/last_mf4_folder"

    def __init__(self, config_dir=None, parent=None, settings=None, tree_root=None):
        super().__init__(parent)
        self.config_dir = Path(config_dir) if config_dir else get_config_dir()
        self.settings = settings or QSettings(self._SETTINGS_ORG, self._SETTINGS_APP)
        self.mf4_folder: Optional[Path] = None
        self.folder_label = None
        self.runner = None
        self.long_checks = {}
        self.lat_checks = {}
        self.tree_root = Path(tree_root) if tree_root else Path(QDir.rootPath())
        self._build_ui()
        self._restore_last_active_folder()

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setMinimumWidth(820)
        self.setStyleSheet(
            """
            QWidget {
                background: #eef1f4;
                color: #111827;
                font-family: 'Inter', 'Helvetica Neue', Arial;
                font-size: 12px;
            }
            QLabel#headline {
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
                color: #0f172a;
            }
            QLabel#badge {
                background: #e2e8f0;
                border-radius: 8px;
                padding: 8px 12px;
                color: #1f2937;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton#primary {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2563eb, stop:1 #0891b2);
                border: none;
                border-radius: 10px;
                padding: 10px;
                color: white;
                font-weight: 700;
                letter-spacing: 0.5px;
                font-size: 13px;
            }
            QPushButton#primary:hover { opacity: 0.9; }
            QPushButton#secondary {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 10px;
                color: #1f2937;
                font-weight: 600;
            }
            QCheckBox {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
                color: #1f2937;
                font-weight: 700;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 14px; height: 14px;
                border-radius: 4px;
                border: 2px solid #3b82f6;
                background: #f8fafc;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
            }
            QTextEdit {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 10px;
                color: #0f172a;
                font-family: 'JetBrains Mono', 'SFMono-Regular', monospace;
                font-size: 13px;
            }
            QTreeView {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                color: #0f172a;
            }
            QTreeView::item { padding: 4px; }
            QTreeView::item:selected {
                background: #e2e8f0;
                color: #0f172a;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        header = QLabel("ADAS KPI Extractor")
        header.setObjectName("headline")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(header)

        badge = QLabel("1) Select MF4 Files  •  2) Pick Features  •  3) Run")
        badge.setObjectName("badge")
        root.addWidget(badge)

        # Main content splitter (left: files, right: features + run + logs)
        splitter = QSplitter(Qt.Horizontal)

        file_panel = self._build_file_panel()
        file_panel.setMinimumWidth(220)
        splitter.addWidget(file_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(14)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Feature selection columns
        selection = QHBoxLayout()
        selection.setSpacing(16)
        long_col = self._build_feature_column("AS_Long", ["AEB", "FCW", "LSAEB", "RPC"], domain="long")
        lat_col = self._build_feature_column("AS_Lat", ["LKA", "LSS"], domain="lat")
        selection.addWidget(long_col, 1)
        selection.addWidget(lat_col, 1)
        right_layout.addLayout(selection)

        right_layout.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Minimum))

        # Run button
        self.btn_run = QPushButton("RUN")
        self.btn_run.setObjectName("primary")
        self.btn_run.setFixedHeight(44)
        self.btn_run.clicked.connect(self.run_selection)
        right_layout.addWidget(self.btn_run)

        # Logs
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs will appear here...")
        right_layout.addWidget(self.log_view, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 520])

        root.addWidget(splitter, 1)

    def _build_feature_column(self, title, options, domain):
        wrapper = QFrame()
        layout = QVBoxLayout(wrapper)
        layout.setSpacing(10)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("headline")
        layout.addWidget(title_lbl)

        for opt in options:
            cb = QCheckBox(opt)
            if domain == "long":
                self.long_checks[opt] = cb
                if opt == "RPC":
                    cb.setEnabled(False)
                    cb.setText(f"{opt} (coming soon)")
            else:
                self.lat_checks[opt] = cb
                if opt == "LSS":
                    cb.setEnabled(False)
                    cb.setText(f"{opt} (coming soon)")
            layout.addWidget(cb)

        layout.addStretch(1)
        return wrapper

    def _build_file_panel(self):
        file_panel = QFrame()
        file_layout = QVBoxLayout(file_panel)
        file_layout.setSpacing(10)

        file_header = QHBoxLayout()
        file_title = QLabel("Target files")
        file_title.setObjectName("headline")
        self.file_count = QLabel("0 selected")
        self.file_count.setObjectName("badge")
        file_header.addWidget(file_title, 1)
        file_header.addWidget(self.file_count, 0)
        file_layout.addLayout(file_header)

        file_buttons = QHBoxLayout()
        btn_select_all = QPushButton("Select all")
        btn_select_all.setObjectName("secondary")
        btn_select_all.clicked.connect(lambda: self._set_all_files_checked(True))
        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("secondary")
        btn_clear.clicked.connect(lambda: self._set_all_files_checked(False))
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setObjectName("secondary")
        btn_refresh.clicked.connect(self._refresh_file_tree)
        file_buttons.addWidget(btn_select_all)
        file_buttons.addWidget(btn_clear)
        file_buttons.addWidget(btn_refresh)
        file_buttons.addStretch(1)
        file_layout.addLayout(file_buttons)

        self.file_model = FileTreeModel(self)
        self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.file_model.setRootPath(str(self.tree_root))
        self.file_model.check_state_changed.connect(self._on_check_state_changed)

        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(str(self.tree_root)))
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setUniformRowHeights(True)
        self.file_tree.setSortingEnabled(True)
        self.file_tree.sortByColumn(0, Qt.AscendingOrder)
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)
        self.file_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_tree.setItemDelegate(FileTreeDelegate(self.file_tree))
        self.file_tree.setTextElideMode(Qt.ElideNone)
        self.file_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        header = self.file_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.file_model.directoryLoaded.connect(lambda _: self.file_tree.resizeColumnToContents(0))
        file_layout.addWidget(self.file_tree, 1)

        return file_panel

    # ---------------- Actions ----------------
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select MF4 Folder", "")
        if folder:
            self._set_active_folder(Path(folder))

    def _set_all_files_checked(self, checked: bool):
        if not checked:
            self.file_model.clear_checks()
            self._update_file_count()
            return

        if not self.mf4_folder:
            self.log("Select a folder to enable Select all.")
            return

        mf4_files = [p for p in self.mf4_folder.glob("*.mf4") if p.is_file()]
        self.file_model.clear_checks()
        self.file_model.set_checked_paths(mf4_files, checked=True)
        self._update_file_count()

    def _update_file_count(self):
        selected = len(self._selected_files())
        self.file_count.setText(f"{selected} selected")

    def _refresh_file_tree(self):
        self.file_model.setRootPath(str(self.tree_root))
        self.file_tree.setRootIndex(self.file_model.index(str(self.tree_root)))
        if self.mf4_folder:
            self._reveal_path_in_tree(self.mf4_folder)

    def _reveal_path_in_tree(self, path: Path):
        idx = self.file_model.index(str(path))
        if not idx.isValid():
            return
        self.file_tree.setCurrentIndex(idx)
        self.file_tree.scrollTo(idx)
        parent = idx.parent()
        while parent.isValid():
            self.file_tree.expand(parent)
            parent = parent.parent()

    def _set_active_folder(self, folder: Path):
        self.mf4_folder = Path(folder).expanduser().resolve()
        if self.folder_label is not None:
            self.folder_label.setText(str(self.mf4_folder))
        self._persist_active_folder()
        self.log(f"MF4 folder set to: {self.mf4_folder}")
        self._reveal_path_in_tree(self.mf4_folder)

    def _persist_active_folder(self):
        if self.mf4_folder is None:
            self.settings.remove(self._LAST_FOLDER_KEY)
        else:
            self.settings.setValue(self._LAST_FOLDER_KEY, str(self.mf4_folder))
        self.settings.sync()

    def _restore_last_active_folder(self):
        folder = self.settings.value(self._LAST_FOLDER_KEY, "", type=str)
        if not folder:
            return

        folder_path = Path(folder).expanduser()
        if not folder_path.exists() or not folder_path.is_dir():
            self.settings.remove(self._LAST_FOLDER_KEY)
            self.settings.sync()
            return

        self.mf4_folder = folder_path.resolve()
        if self.folder_label is not None:
            self.folder_label.setText(str(self.mf4_folder))
        self._reveal_path_in_tree(self.mf4_folder)

    def _on_check_state_changed(self, changed_path="", state=None):
        selected = self._selected_files()
        if not selected:
            self._update_file_count()
            return

        preferred_parent = None
        changed = Path(changed_path).resolve() if changed_path else None
        checked_state = int(getattr(Qt.Checked, "value", Qt.Checked))
        if changed is not None and state == checked_state and changed in selected:
            preferred_parent = changed.parent
        else:
            preferred_parent = selected[0].parent

        if any(p.parent != preferred_parent for p in selected):
            self.file_model.clear_checks_outside_dir(preferred_parent)
            self.log("⚠️ Files must be selected from a single folder; cleared other folders.")
            selected = self._selected_files()
            if not selected:
                self._update_file_count()
                return

        if self.mf4_folder != preferred_parent:
            self.mf4_folder = preferred_parent
            if self.folder_label is not None:
                self.folder_label.setText(str(self.mf4_folder))
            self._persist_active_folder()

        self._update_file_count()

    def _selected_features(self):
        long_selected = [name for name, cb in self.long_checks.items() if cb.isChecked() and cb.isEnabled()]
        lat_selected = [name for name, cb in self.lat_checks.items() if cb.isChecked() and cb.isEnabled()]
        return long_selected, lat_selected

    def _selected_files(self):
        return self.file_model.checked_files()

    def run_selection(self):
        if self.runner and self.runner.isRunning():
            self.log("A run is already in progress.")
            return
        if not self.mf4_folder:
            self.log("Please select an MF4 folder.")
            return
        if not self._selected_files():
            self.log("Please select at least one MF4 file.")
            return

        long_sel, lat_sel = self._selected_features()
        if not long_sel and not lat_sel:
            self.log("Please select at least one feature.")
            return

        self.btn_run.setEnabled(False)
        self.log("Starting run...")
        self.runner = PipelineRunner(
            self.mf4_folder,
            long_sel,
            lat_sel,
            self.config_dir,
            mf4_files=self._selected_files() or None,
        )
        self.runner.log.connect(self.log)
        self.runner.error.connect(self.log)
        self.runner.finished_all.connect(self._on_finished)
        self.runner.start()

    def _on_finished(self):
        self.log("All requested runs completed.")
        self.btn_run.setEnabled(True)

    def log(self, msg):
        self.log_view.append(msg)
