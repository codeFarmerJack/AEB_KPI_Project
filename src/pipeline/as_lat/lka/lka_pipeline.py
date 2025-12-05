from pathlib import Path
from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_lat.lka.lka_event_segmenter import LkaEventSegmenter
from src.pipeline.as_lat.lka.lka_event_kpi_extractor import LkaEventKpiExtractor
from src.pipeline.as_lat.lka.lka_visualizer import LkaVisualizer


class LkaPipeline(BasePipeline):
    """Pipeline orchestrator for LKA KPI extraction and visualization."""

    # --------------------------------------------------------------
    def _detect_events(self):
        print("\n➡️ [3/5] Detecting LKA events...")
        try:
            self.event = LkaEventSegmenter(self.ih, self.cfg)
            print("🚗 Running LKA event detection...\n")
            self.event.process_all_files()
            print("✅ LKA event detection finished.\n")
        except Exception as e:
            raise RuntimeError(f"❌ LKA event detection failed: {e}")

    # --------------------------------------------------------------
    def _extract_kpis(self):
        print("\n➡️ [4/5] Extracting LKA KPIs...")
        try:
            self.kpi = LkaEventKpiExtractor(self.cfg, self.event)
            self.kpi.process_all_mdf_files()
            self.kpi.process_lka_availability(self.kpi.in_path_extracted)
            self.kpi.export_to_excel()
            print("✅ LKA KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ LKA KPI extraction failed: {e}")

    # --------------------------------------------------------------
    def _visualize_results(self):
        print("\n➡️ [5/5] Launching LKA visualization...\n")
        try:
            self.viz = LkaVisualizer(self.cfg, self.kpi)
            self.viz.interactive = getattr(self, "default_interactive", False)
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ LKA visualization failed: {e}")
