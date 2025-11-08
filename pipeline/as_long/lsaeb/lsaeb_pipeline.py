from pathlib import Path
from pipeline.base.base_pipeline import BasePipeline
from pipeline.as_long.lsaeb.lsaeb_event_segmenter import LsaebEventSegmenter
from pipeline.as_long.lsaeb.lsaeb_kpi_extractor import LsaebKpiExtractor
from pipeline.as_long.lsaeb.lsaeb_visualizer import LsaebVisualizer


class LsaebPipeline(BasePipeline):
    """Pipeline orchestrator for LSAEB KPI extraction and visualization."""

    # --------------------------------------------------------------
    def _detect_events(self):
        print("\n➡️ [3/5] Detecting LSAEB events...")
        try:
            self.event = LsaebEventSegmenter(self.ih, self.cfg)
            print("🚦 Running LSAEB event detection...\n")
            self.event.process_all_files()
            print("✅ LSAEB event detection finished.\n")
        except Exception as e:
            raise RuntimeError(f"❌ LSAEB event detection failed: {e}")

    # --------------------------------------------------------------
    def _extract_kpis(self):
        print("\n➡️ [4/5] Extracting LSAEB KPIs...")
        try:
            self.kpi = LsaebKpiExtractor(self.cfg, self.event)
            self.kpi.process_all_mdf_files()
            self.kpi.export_to_excel()
            print("✅ LSAEB KPI extraction and Excel export done.")
        except Exception as e:
            raise RuntimeError(f"❌ LSAEB KPI extraction failed: {e}")

    # --------------------------------------------------------------
    def _visualize_results(self):
        print("\n➡️ [5/5] Launching LSAEB visualization...\n")
        try:
            self.viz = LsaebVisualizer(self.cfg, self.kpi)
            self.viz.interactive = True   # Enable interactive Plotly output
            self.viz.plot()
        except Exception as e:
            raise RuntimeError(f"❌ LSAEB visualization failed: {e}")
