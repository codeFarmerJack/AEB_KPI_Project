from pathlib import Path
from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_long.aeb.aeb_event_segmenter import AebEventSegmenter
from src.pipeline.as_long.aeb.aeb_event_kpi_extractor import AebEventKpiExtractor
from src.pipeline.as_long.aeb.aeb_cycle_kpi_extractor import AebCycleKpiExtractor
from src.pipeline.as_long.aeb.aeb_visualizer import AebVisualizer


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
            # 1) Event-level KPIs
            self.kpi = AebEventKpiExtractor(self.cfg, self.event)
            self.kpi.process_mdf_events()
            self.kpi.export_event_kpis()

            # 2) Cycle/availability KPIs
            self.cycle_kpi = AebCycleKpiExtractor(self.ih, self.cfg)
            self.cycle_kpi.process_mdf_cycles()
            self.cycle_kpi.export_cycle_kpis()

            print("✅ AEB KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ AEB KPI extraction failed: {e}")

    def _visualize_results(self):
        print("\n➡️ [5/5] Launching AEB visualization...\n")
        try:
            self.viz = AebVisualizer(self.cfg, self.kpi)
            self.viz.interactive = getattr(self, "default_interactive", False)
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ AEB visualization failed: {e}")
