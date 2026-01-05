from pathlib import Path
from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_lat.lka.lka_event_segmenter import LkaEventSegmenter
from src.pipeline.as_lat.lka.lka_event_kpi_extractor import LkaEventKpiExtractor
from src.pipeline.as_lat.lka.lka_cycle_kpi_extractor import LkaCycleKpiExtractor
from src.pipeline.as_lat.lka.lka_event_visualizer import LkaEventVisualizer


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
            # ----------------------------------------------------------
            # 1) EVENT KPIs (segment-level)
            # ----------------------------------------------------------
            self.event_kpi = LkaEventKpiExtractor(self.cfg, self.event)
            self.event_kpi.process_mdf_events()     # compute event KPIs
            self.event_kpi.export_event_kpis()      # save event sheet

            # ----------------------------------------------------------
            # 2) CYCLE KPIs
            # ----------------------------------------------------------
            self.cycle_kpi = LkaCycleKpiExtractor(self.ih, self.cfg)
            self.cycle_kpi.process_mdf_cycles()     # compute cycle KPIs
            self.cycle_kpi.export_cycle_kpis()      # save cycle sheet

            print("✅ LKA KPI extraction and Excel export done.\n")

        except Exception as e:
            raise RuntimeError(f"❌ LKA KPI extraction failed: {e}")


    # --------------------------------------------------------------
    def _visualize_results(self):
        print("\n➡️ [5/5] Launching LKA visualization...\n")
        try:
            self.viz = LkaEventVisualizer(self.cfg, self.event_kpi)
            self.viz.interactive = getattr(self, "default_interactive", False)
            self.viz.plot()
            if getattr(self, "cycle_kpi", None) is not None and not self.cycle_kpi.cycle_kpi_table.empty:
                self.cycle_kpi.render_cycle_dashboards(feature_name="LKA")
        except Exception as e:
            raise RuntimeError(f"❌ LKA visualization failed: {e}")
