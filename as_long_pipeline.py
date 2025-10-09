from pathlib import Path
from pipeline.aeb.pipeline import AebPipeline  


# --- Define paths ---
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_kpi_extractor/python/config/Config.json")

# --- Create pipeline instance ---
aeb = AebPipeline(config_path)
# --- Run the full AEB pipeline ---
aeb.run()


