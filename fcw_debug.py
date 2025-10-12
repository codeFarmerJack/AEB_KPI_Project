import numpy as np
from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.fcw.fcw_event_detector import FcwEventDetector
from asammdf import MDF
import pandas as pd


# --- User parameters ---
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_kpi_extractor/python/config/Config.json")


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

    # --- Create FcwEventDetector ---
    event = FcwEventDetector(ih, cfg)
    print("\n🚦 Running event detection...\n")
    event.process_all_files()
    print("✅ Event detection finished.\n")

    # --- KPI Extraction ---
    #kpi = FcwKpiExtractor(cfg, event)
    #kpi.process_all_mdf_files()
    #kpi.export_to_excel()

    # --- Instantiate AebVisualizer (debug mode) ---
    #print("\n🧩 Initializing AebVisualizer...\n")
    #viz = AebVisualizer(cfg, kpi)

    # --- Optional: enable interactive plots ---
    # 👉 Set this to True if you want zoomable pop-ups.
    #    You can also make this conditional on environment if desired.
    

if __name__ == "__main__":
    main()
