import os
import warnings
import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod

from config.config import Config
from pipeline.input_handler import InputHandler


class BasePipeline(ABC):
    """
    BasePipeline
    -------------
    Abstract base class for all KPI processing pipelines (AEB, FCW, etc.)

    Common Steps:
      1. Load configuration (JSON)
      2. Process MF4 files (resample + signal extraction)
      3. Detect events (implemented by subclass)
      4. Extract KPIs (implemented by subclass)
      5. Visualize results (implemented by subclass)
    """

    def __init__(self, config_path: Path, input_handler=None):
        self.config_path = Path(config_path)
        self.cfg         = None
        self.ih          = input_handler
        self.event       = None
        self.kpi         = None
        self.viz         = None
        self.feature     = self.__class__.__name__.replace("Pipeline", "").upper()

    # ------------------------------------------------------------------ #
    def run(self, skip_mf4_processing: bool = False):
        """Run the entire feature pipeline sequentially."""
        print(f"\n🚀 Starting {self.feature} Processing Pipeline...\n")

        # 1️⃣ Load configuration
        self._load_config()

        # 2️⃣ Process MF4 files
        if self.ih is None and not skip_mf4_processing:
            self._process_mf4_files()
        else:
            print("🪄 Using external InputHandler instance.")

        # 3️⃣ Detect events
        self._detect_events()

        # 4️⃣ Extract KPIs
        self._extract_kpis()

        # 5️⃣ Visualize results
        self._visualize_results()

        print(f"\n🎉 {self.feature} Pipeline finished successfully.\n")

    # ------------------------------------------------------------------ #
    def _load_config(self):
        """Step 1: Load Config JSON."""
        print("➡️ [1/5] Loading configuration...")
        if not self.config_path.exists():
            raise FileNotFoundError(f"⚠️ Config file not found: {self.config_path}")
        self.cfg = Config.from_json(self.config_path)
        print(f"✅ Config loaded: {self.config_path}")

        # Optional summaries
        if isinstance(self.cfg.kpi_spec, pd.DataFrame):
            print("\n📑 KPI Specification:")
            print(f"   ➝ Shape: {self.cfg.kpi_spec.shape}")
            print(self.cfg.kpi_spec.head(8).to_string(index=False))
        else:
            print(f"⚠️ Unexpected type for cfg.kpi_spec: {type(self.cfg.kpi_spec)}")

        print("\n⚙️ Calibratables Summary:")
        for cal_name, val in self.cfg.calibratables.items():
            if isinstance(val, dict):
                print(f"   ➝ {cal_name}: dict keys {list(val.keys())}")
            elif isinstance(val, pd.DataFrame):
                print(f"   ➝ {cal_name}: DataFrame shape {val.shape}")
            else:
                print(f"   ➝ {cal_name}: {type(val)}")

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
    @abstractmethod
    def _detect_events(self):
        """Step 3: Detect feature-specific events."""
        pass

    # ------------------------------------------------------------------ #
    @abstractmethod
    def _extract_kpis(self):
        """Step 4: Extract feature-specific KPIs."""
        pass

    # ------------------------------------------------------------------ #
    @abstractmethod
    def _visualize_results(self):
        """Step 5: Visualize feature-specific KPIs."""
        pass
