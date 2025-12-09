from pathlib import Path
from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_long.fcw.fcw_event_segmenter import FcwEventSegmenter
from src.pipeline.as_long.fcw.fcw_event_kpi_extractor import FcwEventKpiExtractor
from src.pipeline.as_long.fcw.fcw_cycle_kpi_extractor import FcwCycleKpiExtractor
from src.pipeline.as_long.fcw.fcw_visualizer import FcwEventVisualizer


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
            # Event-level KPIs
            self.kpi = FcwEventKpiExtractor(self.cfg, self.event)
            self.kpi.process_mdf_events()
            self.kpi.export_event_kpis()

            # Cycle/availability KPIs
            self.cycle_kpi = FcwCycleKpiExtractor(self.ih, self.cfg)
            self.cycle_kpi.process_mdf_cycles()
            self.cycle_kpi.export_cycle_kpis()
            self.cycle_kpi.render_cycle_dashboards(feature_name="FCW")

            print("✅ FCW KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ FCW KPI extraction failed: {e}")

    def _visualize_results(self):
        print("\n➡️ [5/5] Launching FCW visualization...\n")
        try:
            self.viz = FcwEventVisualizer(self.cfg, self.kpi)
            self.viz.interactive = getattr(self, "default_interactive", False)
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ FCW visualization failed: {e}")
