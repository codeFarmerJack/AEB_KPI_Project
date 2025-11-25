import os
import sys
from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler

# Lateral feature pipelines
from pipeline.as_lat.lka.lka_pipeline import LkaPipeline
# Add other lateral pipelines later in same structure


def main(config_file: Path = None):
    """
    Entry point for AS_LAT KPI extractor.
    Can be called by launcher or used standalone.
    """

    # 1) Determine config path
    if config_file is None:
        # Detect PyInstaller bundle
        base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
        config_file = Path(base_path) / "config" / "config_as_lat.json"

    print(f"\n📘 Loading config: {config_file}")

    # 2) Load configuration and initialize shared input handler
    cfg = Config.from_json(config_file)
    ih  = InputHandler(cfg)

    print("🔄 Processing MF4 files (shared for all AS_LAT pipelines)...")
    ih.process_mf4_files()

    print("\n🚀 Running LKA pipeline...")
    lka = LkaPipeline(config_file, input_handler=ih)
    lka.run(skip_mf4_processing=True)

    print("\n🎯 All AS_LAT pipelines completed successfully.\n")


if __name__ == "__main__":
    main()
