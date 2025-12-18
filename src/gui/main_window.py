from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
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
)

from src.gui.controllers.pipeline_runner import PipelineRunner
from src.utils.path_manager import get_config_dir


class KpiGui(QWidget):
    def __init__(self, config_dir=None, parent=None):
        super().__init__(parent)
        self.config_dir = Path(config_dir) if config_dir else get_config_dir()
        self.mf4_folder: Optional[Path] = None
        self.runner = None
        self.long_checks = {}
        self.lat_checks = {}
        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setMinimumWidth(820)
        self.setStyleSheet(
            """
            QWidget {
                background: #0f172a;
                color: #e2e8f0;
                font-family: 'Inter', 'Helvetica Neue', Arial;
                font-size: 12px;
            }
            QLabel#headline {
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
                color: #e2e8f0;
            }
            QLabel#badge {
                background: #1e293b;
                border-radius: 8px;
                padding: 8px 12px;
                color: #cbd5e1;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton#primary {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #3b82f6, stop:1 #06b6d4);
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
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 10px;
                color: #e2e8f0;
                font-weight: 600;
            }
            QCheckBox {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
                color: #e2e8f0;
                font-weight: 700;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 14px; height: 14px;
                border-radius: 4px;
                border: 2px solid #38bdf8;
                background: #0f172a;
            }
            QCheckBox::indicator:checked {
                background: #38bdf8;
            }
            QTextEdit {
                background: #0b1224;
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 10px;
                color: #e2e8f0;
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

        badge = QLabel("1) Select MF4 Folder  •  2) Pick Features  •  3) Run")
        badge.setObjectName("badge")
        root.addWidget(badge)

        # Folder picker
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("color:#cbd5e1;")
        btn_folder = QPushButton("Select MF4 Folder")
        btn_folder.setObjectName("primary")
        btn_folder.clicked.connect(self.select_folder)
        folder_row.addWidget(self.folder_label, 1)
        folder_row.addWidget(btn_folder, 0)
        root.addLayout(folder_row)

        # Feature selection columns
        selection = QHBoxLayout()
        selection.setSpacing(16)
        long_col = self._build_feature_column("AS_Long", ["AEB", "FCW", "LSAEB", "RPC"], domain="long")
        lat_col = self._build_feature_column("AS_Lat", ["LKA", "LSS"], domain="lat")
        selection.addWidget(long_col, 1)
        selection.addWidget(lat_col, 1)
        root.addLayout(selection)

        root.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Minimum))

        # Run button
        self.btn_run = QPushButton("RUN")
        self.btn_run.setObjectName("primary")
        self.btn_run.setFixedHeight(44)
        self.btn_run.clicked.connect(self.run_selection)
        root.addWidget(self.btn_run)

        # Logs
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Logs will appear here...")
        root.addWidget(self.log_view, 1)

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

    # ---------------- Actions ----------------
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select MF4 Folder", "")
        if folder:
            self.mf4_folder = Path(folder)
            self.folder_label.setText(str(self.mf4_folder))
            self.log(f"MF4 folder set to: {self.mf4_folder}")

    def _selected_features(self):
        long_selected = [name for name, cb in self.long_checks.items() if cb.isChecked() and cb.isEnabled()]
        lat_selected = [name for name, cb in self.lat_checks.items() if cb.isChecked() and cb.isEnabled()]
        return long_selected, lat_selected

    def run_selection(self):
        if self.runner and self.runner.isRunning():
            self.log("A run is already in progress.")
            return
        if not self.mf4_folder:
            self.log("Please select an MF4 folder.")
            return

        long_sel, lat_sel = self._selected_features()
        if not long_sel and not lat_sel:
            self.log("Please select at least one feature.")
            return

        self.btn_run.setEnabled(False)
        self.log("Starting run...")
        self.runner = PipelineRunner(self.mf4_folder, long_sel, lat_sel, self.config_dir)
        self.runner.log.connect(self.log)
        self.runner.error.connect(self.log)
        self.runner.finished_all.connect(self._on_finished)
        self.runner.start()

    def _on_finished(self):
        self.log("All requested runs completed.")
        self.btn_run.setEnabled(True)

    def log(self, msg):
        self.log_view.append(msg)
