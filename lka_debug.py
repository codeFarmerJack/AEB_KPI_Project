import numpy as np
import pandas as pd
from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.as_lat.lka.lka_event_segmenter import LkaEventSegmenter
# from pipeline.as_lat.lka.lka_kpi_extractor import LkaKpiExtractor  # optional

# --- User parameters ---
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_kpi_extractor/python/config/config_as_lat.json")

def main():
    # --- Load Config ---
    if not config_path.exists():
        raise FileNotFoundError(f"⚠️ Config file not found: {config_path}")
    cfg = Config.from_json(config_path)

    # --- Display KPI Specification Summary ---
    print("\n📑 KPI Specification (cfg.kpi_spec):")
    if isinstance(cfg.kpi_spec, pd.DataFrame):
        print(f"   ➝ DataFrame shape: {cfg.kpi_spec.shape}")
        print(cfg.kpi_spec.head(8).to_string(index=False))
        print("\n🔎 Columns:", list(cfg.kpi_spec.columns))
    else:
        print(f"⚠️ Unexpected type for cfg.kpi_spec: {type(cfg.kpi_spec)}")

    # --- Create InputHandler ---
    ih = InputHandler(cfg)

    # --- Process MF4 files (convert raw → extracted) ---
    print("\n📂 Processing raw MF4 files...")
    ih.process_mf4_files()

    # --- Run LKA event detection ---
    print("\n🚗 Running LKA event segmentation...\n")
    lka_event = LkaEventSegmenter(ih, cfg)
    lka_event.process_all_files()
    print("✅ LKA event segmentation finished.\n")

    # --- (Optional) KPI extraction ---
    # print("\n📊 Running LKA KPI extraction...\n")
    # kpi_extractor = LkaKpiExtractor(cfg, lka_event)
    # kpi_extractor.process_all_mdf_files()
    # kpi_extractor.export_to_excel()
    # print("✅ LKA KPI extraction finished.\n")

if __name__ == "__main__":
    main()
