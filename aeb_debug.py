import numpy as np
from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.aeb.aeb_event_segmenter import AebEventSegmenter
from pipeline.aeb.aeb_kpi_extractor import AebKpiExtractor
from pipeline.AebVisualizer import AebVisualizer
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

    # --- Create AebEventSegmenter ---
    event = AebEventSegmenter(ih, cfg)
    print("\n🚦 Running event detection...\n")
    event.process_all_files()
    print("✅ Event detection finished.\n")

    # --- KPI Extraction ---
    kpi = AebKpiExtractor(cfg, event)
    kpi.process_all_mdf_files()
    kpi.export_to_excel()

    # --- Instantiate AebVisualizer (debug mode) ---
    print("\n🧩 Initializing AebVisualizer...\n")
    viz = AebVisualizer(cfg, kpi)

    # --- Optional: enable interactive plots ---
    # 👉 Set this to True if you want zoomable pop-ups.
    #    You can also make this conditional on environment if desired.
    viz.interactive = True

    # --- Debug printouts ---
    print(f"📘 graph_spec shape: {viz.graph_spec.shape}")
    print(f"📘 line_colors shape: {viz.line_colors.shape if isinstance(viz.line_colors, pd.DataFrame) else len(viz.line_colors)}")
    print(f"📘 marker_shapes: {viz.marker_shapes.shape if isinstance(viz.marker_shapes, pd.DataFrame) else len(viz.marker_shapes)}")
    print(f"📘 calibratables keys: {list(viz.calibratables.keys())[:5]}")
    print(f"📘 path_to_excel: {viz.path_to_excel}")

    # --- Optional: Inspect graphSpec columns ---
    print("\n🧾 GraphSpec Columns:", list(viz.graph_spec.columns))
    print(viz.graph_spec.head(10).to_string(index=False))

    # --- Run visualization (core debugging target) ---
    print("\n🎨 Launching visualization...\n")
    try:
        viz.plot()
    except Exception as e:
        print(f"❌ Visualization failed: {e}")
        raise

    print("\n✅ Visualization pipeline finished successfully.\n")



if __name__ == "__main__":
    main()
