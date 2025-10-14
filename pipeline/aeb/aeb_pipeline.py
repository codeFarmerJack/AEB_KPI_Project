from pathlib import Path
from pipeline.base.base_pipeline import BasePipeline
from pipeline.aeb.aeb_event_segmenter import AebEventSegmenter
from pipeline.aeb.aeb_kpi_extractor import AebKpiExtractor
from pipeline.aeb.aeb_visualizer import AebVisualizer


class AebPipeline(BasePipeline):
    """Pipeline orchestrator for AEB KPI extraction and visualization."""

    def _detect_events(self):
        print("\n➡️ [3/5] Detecting AEB events...")
        try:
            self.event = AebEventSegmenter(self.ih, self.cfg)
            print("🚦 Running event detection...\n")
            self.event.process_all_files()
            print("✅ AEB event detection finished.\n")
        except Exception as e:
            raise RuntimeError(f"❌ AEB event detection failed: {e}")

    def _extract_kpis(self):
        print("\n➡️ [4/5] Extracting AEB KPIs...")
        try:
            self.kpi = AebKpiExtractor(self.cfg, self.event)
            self.kpi.process_all_mdf_files()
            self.kpi.export_to_excel()
            print("✅ AEB KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ AEB KPI extraction failed: {e}")

    def _visualize_results(self):
        print("\n➡️ [5/5] Launching AEB visualization...\n")
        try:
            self.viz = AebVisualizer(self.cfg, self.kpi)
            self.viz.interactive = True
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ AEB visualization failed: {e}")
