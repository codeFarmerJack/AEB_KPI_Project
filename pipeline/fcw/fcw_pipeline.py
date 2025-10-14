import os
import warnings
import pandas as pd
from pathlib import Path

from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.fcw.fcw_event_segmenter import FcwEventSegmenter
from pipeline.fcw.fcw_kpi_extractor import FcwKpiExtractor
from pipeline.fcw.fcw_visualizer import FcwVisualizer


class FcwPipeline:
    """
    FcwPipeline
    ------------
    High-level orchestrator for the FCW KPI processing pipeline.

    Steps:
      1. Load configuration (JSON)
      2. Process MF4 files (resample + signal extraction)
      3. Detect FCW events
      4. Extract KPIs and export to Excel
      5. Visualize results (interactive or static)
    """

    def __init__(self, config_path: Path, input_handler=None):
        self.config_path = Path(config_path)
        self.cfg         = None
        self.ih          = input_handler   # Optional external InputHandler
        self.event       = None
        self.kpi         = None
        self.viz         = None

    # ------------------------------------------------------------------ #
    def run(self, skip_mf4_processing: bool = False):
        """Run the entire FCW pipeline sequentially."""
        print("\n🚀 Starting FCW Processing Pipeline...\n")

        # 1️⃣ Load configuration
        self._load_config()

        # 2️⃣ Process MF4 files
        if self.ih is None and not skip_mf4_processing:
            self._process_mf4_files()
        else:
            print("🪄 Using external InputHandler instance.")

        # 3️⃣ Detect FCW events
        self._detect_events()

        # 4️⃣ Extract KPIs
        self._extract_kpis()

        # 5️⃣ Visualize results
        self._visualize_results()

        print("\n🎉 FCW Pipeline finished successfully.\n")

    # ------------------------------------------------------------------ #
    def _load_config(self):
        """Step 1: Load Config JSON."""
        print("➡️ [1/5] Loading configuration...")
        if not self.config_path.exists():
            raise FileNotFoundError(f"⚠️ Config file not found: {self.config_path}")
        self.cfg = Config.from_json(self.config_path)
        print(f"✅ Config loaded: {self.config_path}")

        # Optional summary
        print("\n📑 KPI Specification (cfg.kpi_spec):")
        if isinstance(self.cfg.kpi_spec, pd.DataFrame):
            print(f"   ➝ Shape: {self.cfg.kpi_spec.shape}")
            print(self.cfg.kpi_spec.head(8).to_string(index=False))
            print("\n🔎 Columns:", list(self.cfg.kpi_spec.columns))
        else:
            print(f"⚠️ Unexpected type for cfg.kpi_spec: {type(self.cfg.kpi_spec)}")

        # Optional calibration summary
        print("\n⚙️ Calibratables Summary:")
        for cal_name, val in self.cfg.calibratables.items():
            print(f"   ➝ {cal_name}:")
            if isinstance(val, dict):
                print(f"      dict keys: {list(val.keys())}")
            elif isinstance(val, pd.DataFrame):
                print(f"      DataFrame shape: {val.shape}")
            else:
                print(f"      Type: {type(val)} — Value: {val}")

    # ------------------------------------------------------------------ #
    def _process_mf4_files(self):
        """Step 2: Process MF4 files."""
        print("\n➡️ [2/5] Processing MF4 files...")
        try:
            self.ih = InputHandler(self.cfg)
            self.ih.process_mf4_files()
            print("✅ MF4 files processed successfully.")
        except Exception as e:
            raise RuntimeError(f"❌ MF4 processing failed: {e}")

    # ------------------------------------------------------------------ #
    def _detect_events(self):
        """Step 3: Detect FCW events."""
        print("\n➡️ [3/5] Detecting FCW events...")
        try:
            self.event = FcwEventSegmenter(self.ih, self.cfg)
            print("🚦 Running event detection...\n")
            self.event.process_all_files()
            print("✅ Event detection finished.\n")
        except Exception as e:
            raise RuntimeError(f"❌ Event detection failed: {e}")

    # ------------------------------------------------------------------ #
    def _extract_kpis(self):
        """Step 4: Extract KPIs and export to Excel."""
        print("\n➡️ [4/5] Extracting KPIs...")
        try:
            self.kpi = FcwKpiExtractor(self.cfg, self.event)
            self.kpi.process_all_mdf_files()
            self.kpi.export_to_excel()
            print("✅ KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ KPI extraction failed: {e}")

    # ------------------------------------------------------------------ #
    def _visualize_results(self):
        """Step 5: Visualization."""
        print("\n➡️ [5/5] Launching visualization...\n")
        try:
            self.viz = FcwVisualizer(self.cfg, self.kpi)
            self.viz.interactive = True  # enable zoomable interactive plots
            self.viz.plot()
            print("✅ FCW visualization complete.")
        except Exception as e:
            raise RuntimeError(f"❌ Visualization failed: {e}")
