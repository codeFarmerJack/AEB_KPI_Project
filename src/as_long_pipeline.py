import os 
import sys
from pathlib import Path
from typing import Optional, Union
from src.config.config import Config
from src.utils.path_manager import get_config_dir
from src.pipeline.input_handler import InputHandler

# Longitudinal feature pipelines
from src.pipeline.as_long.aeb.aeb_pipeline import AebPipeline
from src.pipeline.as_long.fcw.fcw_pipeline import FcwPipeline
from src.pipeline.as_long.lsaeb.lsaeb_pipeline import LsaebPipeline


def main(config_file: Optional[Union[Path, str]] = None, mf4_folder: Optional[Union[Path, str]] = None, mf4_files=None):
    """
    Entry point for AS_LONG KPI extractor.
    This MUST be callable by the launcher OR standalone.
    """

    # 1) Determine config path
    config_file = Path(config_file) if config_file else get_config_dir() / "config_as_long.json"


    print(f"\n📘 Loading config: {config_file}")

    # 2) Load configuration and initialize shared input handler
    cfg = Config.from_json(config_file)
    ih  = InputHandler(cfg, input_path=mf4_folder, mf4_files=mf4_files)

    print("🔄 Processing MF4 files (shared for all AS_LONG pipelines)...")
    ih.process_mf4_files()

    print("\n🚀 Running AEB pipeline...")
    aeb = AebPipeline(config_file, input_handler=ih)
    aeb.run(skip_mf4_processing=True)

    #print("\n🚀 Running FCW pipeline...")
    #fcw = FcwPipeline(config_file, input_handler=ih)
    #fcw.run(skip_mf4_processing=True)

    #print("\n🚀 Running LSAEB pipeline...")
    #lsaeb = LsaebPipeline(config_file, input_handler=ih)
    #lsaeb.run(skip_mf4_processing=True)

    print("\n🎯 All AS_LONG pipelines completed successfully.\n")


if __name__ == "__main__":
    main()
