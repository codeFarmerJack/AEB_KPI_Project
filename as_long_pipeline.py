from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.aeb.aeb_pipeline import AebPipeline
from pipeline.fcw.fcw_pipeline import FcwPipeline


# --- Define paths ---
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_kpi_extractor/python/config/Config.json")

# --- Shared input handler ---
cfg = Config.from_json(config_path)
ih = InputHandler(cfg)
ih.process_mf4_files()   # Process MF4 files once for both pipelines

# --- Create and run AEB pipeline ---
aeb = AebPipeline(config_path, input_handler=ih)
aeb.run(skip_mf4_processing=True)

# --- Create and run FCW pipeline ---
fcw = FcwPipeline(config_path, input_handler=ih)
fcw.run(skip_mf4_processing=True)

