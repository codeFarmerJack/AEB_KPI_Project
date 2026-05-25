from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QSettings
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
    QSpacerItem,
    QSizePolicy,
    QComboBox,
)

from src.gui.controllers.pipeline_runner import PipelineRunner
from src.utils.path_manager import get_config_dir


class KpiGui(QWidget):
    _SETTINGS_ORG = "JackWang401"
    _SETTINGS_APP = "ADAS_KPI_Extractor"
    _LAST_FOLDER_KEY = "gui/last_mf4_folder"
    _LAST_SOURCE_KEY = "gui/last_signal_source"
    _SOURCE_OPTIONS = {
        "Roadcast Log": "roadcast_log",
        "MOTION_1": "motion_1",
    }

    def __init__(self, config_dir=None, parent=None, settings=None, tree_root=None):
        super().__init__(parent)
        self.config_dir = Path(config_dir) if config_dir else get_config_dir()
        self.settings = settings or QSettings(self._SETTINGS_ORG, self._SETTINGS_APP)
        self.mf4_folder: Optional[Path] = None
        self.folder_label = None
        self.file_count = None
        self.selected_files_label = None
        self.selected_mf4_files = []
        self.source_combo = None
        self.runner = None
        self.long_checks = {}
        self.lat_checks = {}
        self._build_ui()
        self._restore_signal_source()
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
            QComboBox {
                background: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 10px;
                color: #1f2937;
                font-weight: 600;
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
            """
        )

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        header = QLabel("ADAS KPI Extractor")
        header.setObjectName("headline")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(header)

        badge = QLabel("1) Select MF4 Files  •  2) Pick Source  •  3) Pick Features  •  4) Run")
        badge.setObjectName("badge")
        root.addWidget(badge)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(14)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(self._build_file_picker())

        source_row = QHBoxLayout()
        source_label = QLabel("Input source")
        source_label.setObjectName("headline")
        self.source_combo = QComboBox()
        self.source_combo.addItems(list(self._SOURCE_OPTIONS.keys()))
        self.source_combo.currentTextChanged.connect(self._persist_signal_source)
        source_row.addWidget(source_label)
        source_row.addWidget(self.source_combo, 1)
        right_layout.addLayout(source_row)

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

        root.addWidget(right_panel, 1)

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

    def _build_file_picker(self):
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
        btn_pick = QPushButton("Pick MF4 files")
        btn_pick.setObjectName("secondary")
        btn_pick.clicked.connect(self.select_files)
        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("secondary")
        btn_clear.clicked.connect(self.clear_selected_files)
        file_buttons.addWidget(btn_pick)
        file_buttons.addWidget(btn_clear)
        file_buttons.addStretch(1)
        file_layout.addLayout(file_buttons)

        self.selected_files_label = QLabel("No files selected")
        self.selected_files_label.setObjectName("badge")
        self.selected_files_label.setWordWrap(True)
        file_layout.addWidget(self.selected_files_label)

        return file_panel

    # ---------------- Actions ----------------
    def select_files(self):
        start_dir = str(self.mf4_folder) if self.mf4_folder else ""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select MF4 Files",
            start_dir,
            "MF4 files (*.mf4 *.MF4);;All files (*)",
        )
        if files:
            self._set_selected_files(files)

    def clear_selected_files(self):
        self.selected_mf4_files = []
        self._update_file_count()

    def _update_file_count(self):
        selected = len(self._selected_files())
        if self.file_count is not None:
            self.file_count.setText(f"{selected} selected")
        if self.selected_files_label is None:
            return
        if not selected:
            self.selected_files_label.setText("No files selected")
        elif selected == 1:
            self.selected_files_label.setText(self.selected_mf4_files[0].name)
        else:
            first = self.selected_mf4_files[0].name
            self.selected_files_label.setText(f"{first} + {selected - 1} more")

    def _set_active_folder(self, folder: Path):
        self.mf4_folder = Path(folder).expanduser().resolve()
        if self.folder_label is not None:
            self.folder_label.setText(str(self.mf4_folder))
        self._persist_active_folder()
        self.log(f"MF4 folder set to: {self.mf4_folder}")

    def _set_selected_files(self, files):
        selected = [Path(p).expanduser().resolve() for p in files]
        selected = [p for p in selected if p.suffix.lower() == ".mf4"]
        if not selected:
            self.log("Please select at least one MF4 file.")
            return

        parent = selected[0].parent
        if any(p.parent != parent for p in selected):
            self.log("Files must be selected from a single folder.")
            return

        self.selected_mf4_files = selected
        self.mf4_folder = parent
        self._persist_active_folder()
        self._update_file_count()
        self.log(f"Selected {len(selected)} MF4 file(s) from: {self.mf4_folder}")

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
        self._restore_signal_source()

    def _selected_signal_source(self):
        if self.source_combo is None:
            return "roadcast_log"
        return self._SOURCE_OPTIONS.get(self.source_combo.currentText(), "roadcast_log")

    def _persist_signal_source(self):
        if self.source_combo is None:
            return
        self.settings.setValue(self._LAST_SOURCE_KEY, self.source_combo.currentText())
        self.settings.sync()

    def _restore_signal_source(self):
        if self.source_combo is None:
            return
        source_label = self.settings.value(self._LAST_SOURCE_KEY, "Roadcast Log", type=str)
        if source_label in self._SOURCE_OPTIONS:
            self.source_combo.setCurrentText(source_label)

    def _selected_features(self):
        long_selected = [name for name, cb in self.long_checks.items() if cb.isChecked() and cb.isEnabled()]
        lat_selected = [name for name, cb in self.lat_checks.items() if cb.isChecked() and cb.isEnabled()]
        return long_selected, lat_selected

    def _selected_files(self):
        return list(self.selected_mf4_files)

    def run_selection(self):
        if self.runner and self.runner.isRunning():
            self.log("A run is already in progress.")
            return
        if not self._selected_files():
            self.select_files()
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
            signal_source=self._selected_signal_source(),
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
