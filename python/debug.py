import json
from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.aeb.event_detector import EventDetector
from pipeline.aeb.kpi_extractor import KPIExtractor
from asammdf import MDF
import pandas as pd


# --- User parameters (edit as needed) ---
mf4_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/rawdata")
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_matlab/01_kpi_extractor/AEB_KPI_PROJECT/python/config/Config.json")
resample_rate = 0.01   # 100 Hz
pre_time = 6.0
post_time = 3.0


def main():
    # --- Load config ---
    if not config_path.exists():
        raise FileNotFoundError(f"⚠️ Config file not found: {config_path}")
    cfg = Config.from_json(config_path)

    # Implement the logic to visulize the content of cfg.kpi_spec
    # --- Visualize cfg.kpi_spec ---
    print("\n📑 KPI Specification (cfg.kpi_spec):")

    if hasattr(cfg, "kpi_spec"):
        kpi_spec = cfg.kpi_spec

        if isinstance(kpi_spec, pd.DataFrame):
            print(f"   ➝ DataFrame with shape {kpi_spec.shape}")
            print(kpi_spec.head(10).to_string(index=False))

            # Optional: pretty summary
            print("\n🔎 Column names:", list(kpi_spec.columns))
            print("📌 Example KPI names:", kpi_spec['name'].head(5).tolist())

        elif isinstance(kpi_spec, dict): 
            print(json.dumps(kpi_spec, indent=4))
        else:
            print(f"   ➝ Type: {type(kpi_spec)}")
            print(kpi_spec)
    else:
        print("⚠️ cfg has no attribute 'kpi_spec'")

    print("\n⚙️ Calibratables (cfg.calibratables):")
    for sheet_name, cal_defs in cfg.calibratables.items():
        print(f"\n📂 Sheet: {sheet_name}")
        for cal_name, val in cal_defs.items():
            if isinstance(val, dict) and "x" in val and "y" in val:
                print(f"   ➝ {cal_name}: Lookup Table")
                print(json.dumps(val, indent=4))
            elif isinstance(val, pd.DataFrame):
                if not val.empty:
                    print(f"   ➝ {cal_name}: DataFrame {val.shape}")
                    print(val.to_json(orient="records", indent=4))
                else:
                    print(f"   ➝ {cal_name}: (empty DataFrame)")
            elif val is None:
                print(f"   ➝ {cal_name}: (empty)")
            else:
                print(f"   ➝ {cal_name}: {val}")




    # --- Create InputHandler instance ---
    ih = InputHandler(cfg)

    # --- Process MF4 files (resample + save as *_extracted.mf4) ---
    ih.process_mf4_files(resample_rate=resample_rate)

    # --- Inspect only *_extracted.mf4 files ---
    mdf_files = list(mf4_path.glob("*_extracted.mf4"))
    print(f"\n📂 Found {len(mdf_files)} extracted MF4 files in {mf4_path}\n")

    for mf4_file in mdf_files:
        print(f"🔍 Inspecting {mf4_file.name}")
        mdf = MDF(mf4_file)

        # Print global header
        print("   ➝ Global Info:")
        print(f"      Start time: {mdf.header.start_time}")
        print(f"      Time comment: {mdf.header.comment}")
        print(f"      Number of channels: {len(mdf.channels_db)}")

        print("   ➝ Available signals:")
        for i, (ch_name, ch_info) in enumerate(mdf.channels_db.items()):
            if isinstance(ch_info, tuple) and len(ch_info) > 1:
                channel = ch_info[1]
            else:
                channel = ch_info

            unit = getattr(channel, "unit", "")
            print(f"      {i+1:3d}. {ch_name} [{unit}]")
            if i >= 14:
                print("      ... (list truncated)")
                break


        # Print events in the file
        if mdf.events:
            print("   ➝ Events in file:")
            for ev in mdf.events:
                print(f"      - {ev['name']} @ {ev['time_offset']}s")
        else:
            print("   ➝ No events in file")

        print("-" * 60)

    # --- Create EventDetector instance ---
    event = EventDetector(ih, pre_time=pre_time, post_time=post_time)

    # --- Run event detection + extraction (only *_extracted.mf4) ---
    print("\n🚦 Running event detection + chunk extraction...\n")
    event.process_all_files()
    print("\n✅ Event detection and extraction finished.\n")

    kpi = KPIExtractor(cfg, event)
    kpi.process_all_mdf_files()   # don’t forget this step, otherwise table is empty
    kpi.export_to_csv()


if __name__ == "__main__":
    main()