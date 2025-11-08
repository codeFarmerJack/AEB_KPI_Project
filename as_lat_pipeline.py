from pathlib import Path
from config.config import Config
from pipeline.input_handler import InputHandler
from pipeline.as_lat.lka.lka_pipeline import LkaPipeline
# (🔧 Add other as_lat pipelines here later, e.g., LaneDeparturePipeline)

# ============================================================
# 🔧 Configuration & Setup
# ============================================================
config_path = Path("/Users/wangjianhai/02_ADAS/01_repo/01_Tools/01_kpi_extractor/python/config/config_as_lat.json")

# --- Load config and initialize input handler ---
cfg = Config.from_json(config_path)
ih  = InputHandler(cfg)

ih.process_mf4_files()   # Run once for all as_lat pipelines

lka = LkaPipeline(config_path, input_handler=ih)
lka.run(skip_mf4_processing=True)

print("\n🎯 All as_lat pipelines completed successfully.\n")
