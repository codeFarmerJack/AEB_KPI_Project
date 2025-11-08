import numpy as np
from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.as_long.lsaeb.lsaeb_event_segmenter import LsaebEventSegmenter
from pipeline.as_long.lsaeb.lsaeb_kpi_extractor import LsaebKpiExtractor
from pipeline.as_long.lsaeb.lsaeb_visualizer import LsaebVisualizer
import pandas as pd


# --- User parameters ---
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_kpi_extractor/python/config/config_as_long.json")


def main():
    # --- Load config ---
    if not config_path.exists():
        raise FileNotFoundError(f"⚠️ Config file not found: {config_path}")
    cfg = Config.from_json(config_path)

    # --- Display KPI Spec Summary ---
    print("\n📑 KPI Specification (cfg.kpi_spec):")
    if isinstance(cfg.kpi_spec, pd.DataFrame):
        print(f"   ➝ DataFrame shape: {cfg.kpi_spec.shape}")
        print(cfg.kpi_spec.head(8).to_string(index=False))
        print("\n🔎 Columns:", list(cfg.kpi_spec.columns))
    else:
        print(f"⚠️ Unexpected type for cfg.kpi_spec: {type(cfg.kpi_spec)}")

    # --- Display Calibration Overview ---
    print("\n⚙️ Calibratables Summary:")
    for cal_name, val in cfg.calibratables.items():
        print(f"   ➝ {cal_name}:")
        if isinstance(val, dict):
            print(f"      Type: dict with keys {list(val.keys())}")
            for key, sub_val in val.items():
                if isinstance(sub_val, (list, np.ndarray)):
                    print(f"        {key}: {sub_val}")
                else:
                    print(f"        {key}: {sub_val}")
        elif isinstance(val, pd.DataFrame):
            print(f"      Type: DataFrame {val.shape}")
            print(f"      Columns: {list(val.columns)}")
            print(f"      Head:\n{val.head().to_string()}")
        else:
            print(f"      Type: {type(val)}")
            print(f"      Value: {val}")

    # --- Create InputHandler ---
    ih = InputHandler(cfg)

    # --- Process MF4 files ---
    ih.process_mf4_files()

    # --- Create LsaebEventSegmenter ---
    event = LsaebEventSegmenter(ih, cfg)
    print("\n🚦 Running LSAEB event detection...\n")
    event.process_all_files()
    print("✅ LSAEB event detection finished.\n")

    # --- Create LsaebKpiExtractor ---
    kpi_extractor = LsaebKpiExtractor(cfg, event)
    print("\n📊 Running LSAEB KPI extraction...\n")
    kpi_extractor.process_all_mdf_files()
    kpi_extractor.export_to_excel()
    print("✅ LSAEB KPI extraction finished.\n")

    # --- Visualization stage ---
    print("\n➡️ [5/5] Launching LSAEB visualization...\n")
    try:
        viz = LsaebVisualizer(cfg, kpi_extractor)
        viz.plot()
    except Exception as e:
        print(f"⚠️ Visualization failed: {e}")

if __name__ == "__main__":
    main()
