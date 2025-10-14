from pathlib import Path
from pipeline.base.base_pipeline import BasePipeline
from pipeline.fcw.fcw_event_segmenter import FcwEventSegmenter
from pipeline.fcw.fcw_kpi_extractor import FcwKpiExtractor
from pipeline.fcw.fcw_visualizer import FcwVisualizer


class FcwPipeline(BasePipeline):
    """Pipeline orchestrator for FCW KPI extraction and visualization."""

    def _detect_events(self):
        print("\n➡️ [3/5] Detecting FCW events...")
        try:
            self.event = FcwEventSegmenter(self.ih, self.cfg)
            print("🚦 Running FCW event detection...\n")
            self.event.process_all_files()
            print("✅ FCW event detection finished.\n")
        except Exception as e:
            raise RuntimeError(f"❌ FCW event detection failed: {e}")

    def _extract_kpis(self):
        print("\n➡️ [4/5] Extracting FCW KPIs...")
        try:
            self.kpi = FcwKpiExtractor(self.cfg, self.event)
            self.kpi.process_all_mdf_files()
            self.kpi.export_to_excel()
            print("✅ FCW KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ FCW KPI extraction failed: {e}")

    def _visualize_results(self):
        print("\n➡️ [5/5] Launching FCW visualization...\n")
        try:
            self.viz = FcwVisualizer(self.cfg, self.kpi)
            self.viz.interactive = True
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ FCW visualization failed: {e}")
