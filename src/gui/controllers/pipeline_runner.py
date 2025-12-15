import sys
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QThread, Signal

from src.config.config import Config
from src.pipeline.input_handler import InputHandler
from src.pipeline.as_long.aeb.aeb_pipeline import AebPipeline
from src.pipeline.as_long.fcw.fcw_pipeline import FcwPipeline
from src.pipeline.as_long.lsaeb.lsaeb_pipeline import LsaebPipeline
from src.pipeline.as_lat.lka.lka_pipeline import LkaPipeline
from src.utils.path_manager import get_config_dir


class _SignalWriter:
    """Redirects stdout/stderr into a Qt signal while mirroring to the original stream."""

    def __init__(self, signal: Signal, mirror):
        self.signal = signal
        self.mirror = mirror

    def write(self, text: str):
        if self.mirror:
            self.mirror.write(text)
        if not text:
            return
        for line in text.splitlines():
            line = line.strip("\n")
            if line:
                self.signal.emit(line)

    def flush(self):
        if self.mirror:
            self.mirror.flush()


class PipelineRunner(QThread):
    """
    Runs selected KPI pipelines off the UI thread and streams logs back to the GUI.
    """

    log = Signal(str)
    finished_all = Signal()
    error = Signal(str)

    LONG_FEATURES = {
        "AEB": AebPipeline,
        "FCW": FcwPipeline,
        "LSAEB": LsaebPipeline,
    }
    LAT_FEATURES = {
        "LKA": LkaPipeline,
    }

    def __init__(self, mf4_folder: Path, features_long: Iterable[str], features_lat: Iterable[str], config_dir: Optional[Path] = None):
        super().__init__()
        self.mf4_folder = Path(mf4_folder).expanduser().resolve()
        self.features_long = [f for f in features_long if f in self.LONG_FEATURES]
        self.features_lat = [f for f in features_lat if f in self.LAT_FEATURES]
        self.config_dir = Path(config_dir) if config_dir else get_config_dir()

    # ------------------ Helpers ------------------ #
    @contextmanager
    def _capture_output(self):
        stdout_old, stderr_old = sys.stdout, sys.stderr
        proxy = _SignalWriter(self.log, stdout_old)
        sys.stdout = sys.stderr = proxy
        try:
            yield
        finally:
            sys.stdout, sys.stderr = stdout_old, stderr_old

    def _run_domain(self, feature_keys, config_name, feature_map):
        if not feature_keys:
            return

        cfg_path = self.config_dir / config_name
        self.log.emit(f"📘 Config: {cfg_path.name}")
        cfg = Config.from_json(cfg_path)
        ih = InputHandler(cfg, input_path=self.mf4_folder)
        ih.process_mf4_files()

        for key in feature_keys:
            pipeline_cls = feature_map[key]
            self.log.emit(f"▶ Running {key} ...")
            try:
                pipeline = pipeline_cls(cfg_path, input_handler=ih)
                pipeline.default_interactive = False
                pipeline.run(skip_mf4_processing=True)
                self.log.emit(f"✅ Finished {key}")
            except Exception as exc:  # noqa: BLE001
                tb = traceback.format_exc()
                self.error.emit(f"❌ {key} failed: {exc}")
                self.log.emit(tb)
                raise

    # ------------------ Main worker ------------------ #
    def run(self):
        if not self.features_long and not self.features_lat:
            self.log.emit("⚠️ No features selected.")
            self.finished_all.emit()
            return

        if not self.mf4_folder.exists():
            self.error.emit(f"MF4 folder not found: {self.mf4_folder}")
            self.finished_all.emit()
            return

        try:
            with self._capture_output():
                self._run_domain(self.features_long, "config_as_long.json", self.LONG_FEATURES)
                self._run_domain(self.features_lat, "config_as_lat.json", self.LAT_FEATURES)
        except Exception:
            # errors already emitted
            pass

        self.finished_all.emit()
