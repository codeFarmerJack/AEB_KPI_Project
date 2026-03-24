from pathlib import Path
from typing import Optional, Union

from src.config.config import Config
from src.pipeline.input_handler import InputHandler
from src.pipeline.registry import get_config_name, get_feature_map
from src.utils.path_manager import get_config_dir


def main(
    config_file: Optional[Union[Path, str]] = None,
    mf4_folder: Optional[Union[Path, str]] = None,
    mf4_files=None,
    feature_keys=None,
):
    """
    Entry point for AS_LONG KPI extractor.
    This MUST be callable by the launcher OR standalone.
    """

    feature_map = get_feature_map("as_long")
    selected_keys = list(feature_keys) if feature_keys else list(feature_map.keys())
    config_name = get_config_name("as_long")
    config_file = Path(config_file) if config_file else get_config_dir() / config_name

    print(f"\n📘 Loading config: {config_file}")

    cfg = Config.from_json(config_file)
    ih = InputHandler(cfg, input_path=mf4_folder, mf4_files=mf4_files)

    print("🔄 Processing MF4 files (shared for all AS_LONG pipelines)...")
    ih.process_mf4_files()

    for key in selected_keys:
        pipeline_cls = feature_map[key]
        print(f"\n🚀 Running {key} pipeline...")
        pipeline = pipeline_cls(config_file, input_handler=ih)
        pipeline.run(skip_mf4_processing=True)

    print("\n🎯 All AS_LONG pipelines completed successfully.\n")


if __name__ == "__main__":
    main()
