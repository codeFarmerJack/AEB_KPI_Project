import os
import warnings
import pandas as pd
from pathlib import Path

from config.config import Config
from pipeline.aeb.aeb_event_segmenter import AebEventSegmenter
from pipeline.aeb.aeb_kpi_extractor import AebKpiExtractor
from pipeline.aeb.visualizer import AebVisualizer


class AebPipeline:
    """
    AebPipeline
    ------------
    High-level orchestrator for the AEB KPI processing pipeline.

    Steps:
      1. Load configuration (JSON)
      2. Process MF4 files (resample + signal extraction)
      3. Detect AEB events
      4. Extract KPIs and export to Excel
      5. Visualize results (interactive or static)
    """

    def __init__(self, config_path: Path, input_handler=None):
        self.config_path = Path(config_path)
        self.cfg         = None
        self.ih          = input_handler   # can be injected externally
        self.event       = None
        self.kpi         = None
        self.viz         = None

    # ------------------------------------------------------------------ #
    def run(self, skip_mf4_processing: bool = False):
        """Run the entire AEB pipeline sequentially."""
        print("\n🚀 Starting AEB Processing Pipeline...\n")

        # 1️⃣ Load configuration
        self._load_config()

        # 2️⃣ Process MF4 files (skip if external handler already provided)
        if self.ih is None and not skip_mf4_processing:
            self._process_mf4_files()
        else:
            print("🪄 Using external InputHandler instance.")

        # 3️⃣ Run event detection
        self._detect_events()

        # 4️⃣ Extract KPIs
        self._extract_kpis()

        # 5️⃣ Visualize results
        self._visualize_results()

        print("\n🎉 AEB Pipeline finished successfully.\n")

    # ------------------------------------------------------------------ #
    def _load_config(self):
        """Step 1: Load Config JSON."""
        print("➡️ [1/5] Loading configuration...")
        if not self.config_path.exists():
            raise FileNotFoundError(f"⚠️ Config file not found: {self.config_path}")
        self.cfg = Config.from_json(self.config_path)
        print(f"✅ Config loaded: {self.config_path}")

    # ------------------------------------------------------------------ #
    def _process_mf4_files(self):
        """Step 2: Process MF4 files using InputHandler."""
        print("\n➡️ [2/5] Processing MF4 files...")
        from pipeline.input_handler import InputHandler  # imported only when needed
        try:
            self.ih = InputHandler(self.cfg)
            self.ih.process_mf4_files()
            print("✅ MF4 files processed successfully.")
        except Exception as e:
            raise RuntimeError(f"❌ MF4 processing failed: {e}")

    # ------------------------------------------------------------------ #
    def _detect_events(self):
        """Step 3: Detect AEB events."""
        print("\n➡️ [3/5] Detecting AEB events...")
        try:
            self.event = AebEventSegmenter(self.ih, self.cfg)
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
            self.kpi = AebKpiExtractor(self.cfg, self.event)
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
            self.viz = AebVisualizer(self.cfg, self.kpi)
            self.viz.interactive = True  # enable zoomable interactive plots
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ Visualization failed: {e}")
