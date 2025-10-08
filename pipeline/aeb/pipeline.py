import os
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from asammdf import MDF

from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.aeb.event_detector import EventDetector
from pipeline.aeb.kpi_extractor import KPIExtractor
from pipeline.visualizer import Visualizer


class AEBPipeline:
    """
    AEBPipeline
    -----------
    Orchestrates the full AEB data processing pipeline.

    Steps:
      1. Load configuration (JSON)
      2. Process MF4 files (resample & extract)
      3. Detect AEB events
      4. Extract KPIs
      5. Visualize results (interactive or static)
    """

    def __init__(
        self,
        config_path: str,
        mf4_path: str,
        resample_rate: float = 0.01,
        pre_time: float      = 6.0,
        post_time: float     = 3.0,
    ):
        self.config_path     = Path(config_path)
        self.mf4_path        = Path(mf4_path)
        self.resample_rate   = resample_rate
        self.pre_time        = pre_time
        self.post_time       = post_time

        if not self.config_path.exists():
            raise FileNotFoundError(f"⚠️ Config file not found: {self.config_path}")

        print(f"\n📁 Using configuration: {self.config_path}")
        print(f"📂 Raw data path: {self.mf4_path}")
        print(f"⚙️ Resample rate: {self.resample_rate} s | Pre: {self.pre_time}s | Post: {self.post_time}s\n")

        # --- Initialize components ---
        self.cfg    = None
        self.ih     = None
        self.event  = None
        self.kpi    = None
        self.viz    = None

    # ------------------------------------------------------------------ #
    def run(self):
        """Run the complete AEB processing pipeline."""
        print("\n🚀 Starting AEB Processing Pipeline...\n")

        # Step 1: Load config
        print("➡️ [1/6] Loading Config...")
        try:
            self.cfg = Config.from_json(self.config_path)
            print("✅ Config loaded successfully.")
        except Exception as e:
            sys.exit(f"❌ Failed to load Config: {e}")

        # Step 2: Display KPI and calibration summary
        self._print_config_summaries()

        # Step 3: Process MF4 files
        print("\n➡️ [2/6] Processing MF4 files...")
        try:
            self.ih = InputHandler(self.cfg)
            self.ih.process_mf4_files(resample_rate=self.resample_rate)
            print("✅ MF4 files processed successfully.")
        except Exception as e:
            sys.exit(f"❌ Failed during MF4 processing: {e}")

        # Step 4: Inspect extracted MF4s
        self._inspect_mf4_files()

        # Step 5: Run event detection
        print("\n➡️ [3/6] Detecting AEB events...")
        try:
            self.event = EventDetector(self.ih, pre_time=self.pre_time, post_time=self.post_time)
            self.event.process_all_files()
            print("✅ Event detection completed.")
        except Exception as e:
            sys.exit(f"❌ Failed during event detection: {e}")

        # Step 6: Extract KPIs
        print("\n➡️ [4/6] Extracting KPIs...")
        try:
            self.kpi = KPIExtractor(self.cfg, self.event)
            self.kpi.process_all_mdf_files()
            self.kpi.export_to_excel()
            print("✅ KPI extraction & Excel export done.")
        except Exception as e:
            sys.exit(f"❌ Failed during KPI extraction: {e}")

        # Step 7: Visualization
        print("\n➡️ [5/6] Launching visualization...")
        try:
            self.viz = Visualizer(self.cfg, self.kpi)
            self.viz.interactive = True  # enable zoomable pop-ups
            self._print_visualizer_summary()
            self.viz.plot()
            print("✅ Visualization completed successfully.")
        except Exception as e:
            sys.exit(f"❌ Visualization failed: {e}")

        print("\n🎉 AEB pipeline finished successfully!\n")

    # ------------------------------------------------------------------ #
    def _print_config_summaries(self):
        """Helper: print summaries of KPI spec and calibratables."""
        print("\n📑 KPI Specification (cfg.kpi_spec):")
        if isinstance(self.cfg.kpi_spec, pd.DataFrame):
            print(f"   ➝ Shape: {self.cfg.kpi_spec.shape}")
            print(self.cfg.kpi_spec.head(8).to_string(index=False))
            print("🔎 Columns:", list(self.cfg.kpi_spec.columns))
        else:
            print(f"⚠️ Unexpected type for cfg.kpi_spec: {type(self.cfg.kpi_spec)}")

        print("\n⚙️ Calibratables Summary:")
        for cal_name, val in self.cfg.calibratables.items():
            print(f"   ➝ {cal_name}:")
            if isinstance(val, dict):
                print(f"      Type: dict ({list(val.keys())})")
            elif isinstance(val, pd.DataFrame):
                print(f"      Type: DataFrame {val.shape}, Columns: {list(val.columns)}")
            else:
                print(f"      {type(val)}: {val}")

    # ------------------------------------------------------------------ #
    def _inspect_mf4_files(self):
        """Inspect extracted MF4 files after InputHandler processing."""
        mdf_files = list(self.mf4_path.glob("*_extracted.mf4"))
        print(f"\n📂 Found {len(mdf_files)} extracted MF4 files.")
        if not mdf_files:
            warnings.warn("⚠️ No extracted MF4 files found — check InputHandler output path.")
            return

        try:
            first_file = MDF(mdf_files[0])
            print(f"🧾 Example MF4: {mdf_files[0].name}")
            print(f"   ➝ Channels: {len(first_file.channels_db)}")
        except Exception as e:
            warnings.warn(f"⚠️ Could not inspect MF4 file: {e}")

    # ------------------------------------------------------------------ #
    def _print_visualizer_summary(self):
        """Print visualizer debug info."""
        if not self.viz:
            return
        print(f"\n📘 graph_spec shape: {getattr(self.viz.graph_spec, 'shape', 'N/A')}")
        if isinstance(self.viz.line_colors, pd.DataFrame):
            print(f"📘 line_colors shape: {self.viz.line_colors.shape}")
        else:
            print(f"📘 line_colors entries: {len(self.viz.line_colors)}")
        if isinstance(self.viz.marker_shapes, pd.DataFrame):
            print(f"📘 marker_shapes shape: {self.viz.marker_shapes.shape}")
        else:
            print(f"📘 marker_shapes entries: {len(self.viz.marker_shapes)}")
        print(f"📘 calibratables keys (first 5): {list(self.viz.calibratables.keys())[:5]}")
        print(f"📘 path_to_excel: {self.viz.path_to_excel}")
