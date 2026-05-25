import pandas as pd
from pathlib import Path

from src.config.config import Config
from src.pipeline.input_handler import InputHandler
from src.utils.output_naming import build_kpi_result_filename


class BasePipeline:
    """
    Shared pipeline orchestration for all KPI features.

    Feature pipelines extend this class declaratively by assigning component
    classes instead of re-implementing the same control flow.
    """

    FEATURE_NAME = "BASE"
    SEGMENTER_CLS = None
    EVENT_EXTRACTOR_CLS = None
    CYCLE_EXTRACTOR_CLS = None
    EVENT_VISUALIZER_CLS = None
    CYCLE_DASHBOARD_FEATURE = None

    def __init__(self, config_path: Path, input_handler=None):
        self.config_path = Path(config_path)
        self.cfg = None
        self.ih = input_handler
        self.event = None
        self.kpi = None
        self.event_kpi = None
        self.cycle_kpi = None
        self.viz = None
        self.feature = self.FEATURE_NAME
        self.default_interactive = False

    def run(self, skip_mf4_processing: bool = False):
        """Run the feature pipeline sequentially."""
        print(f"\n🚀 Starting {self.feature} Processing Pipeline...\n")

        self._load_config()

        if self.ih is None and not skip_mf4_processing:
            self._process_mf4_files()
        else:
            print("🪄 Using external InputHandler instance.")

        self._sync_output_filename()
        self._detect_events()
        self._extract_kpis()
        self._visualize_results()

        print(f"\n🎉 {self.feature} Pipeline finished successfully.\n")

    def _load_config(self):
        """Step 1: Load config JSON and print a short summary."""
        print("➡️ [1/5] Loading configuration...")
        if not self.config_path.exists():
            raise FileNotFoundError(f"⚠️ Config file not found: {self.config_path}")

        self.cfg = Config.from_json(self.config_path)
        if self.ih is not None:
            self.cfg.signal_source = getattr(self.ih, "signal_source", "roadcast_log")
        print(f"✅ Config loaded: {self.config_path}")

        if isinstance(self.cfg.event_kpi_list, pd.DataFrame):
            print("\n📑 KPI Specification:")
            print(f"   ➝ Shape: {self.cfg.event_kpi_list.shape}")
            print(self.cfg.event_kpi_list.head(8).to_string(index=False))
        else:
            print(f"⚠️ Unexpected type for cfg.event_kpi_list: {type(self.cfg.event_kpi_list)}")

        print("\n⚙️ Calibratables Summary:")
        for cal_name, val in self.cfg.calibratables.items():
            if isinstance(val, dict):
                print(f"   ➝ {cal_name}: dict keys {list(val.keys())}")
            elif isinstance(val, pd.DataFrame):
                print(f"   ➝ {cal_name}: DataFrame shape {val.shape}")
            else:
                print(f"   ➝ {cal_name}: {type(val)}")

    def _process_mf4_files(self):
        """Step 2: Process MF4 files."""
        print("\n➡️ [2/5] Processing MF4 files...")
        try:
            self.ih = InputHandler(self.cfg)
            self.ih.process_mf4_files()
            print("✅ MF4 files processed successfully.")
        except Exception as exc:
            raise RuntimeError(f"❌ MF4 processing failed: {exc}") from exc

    def _sync_output_filename(self):
        if self.cfg is None or self.ih is None:
            return
        self.cfg.kpi_result_filename = build_kpi_result_filename(
            getattr(self.cfg, "kpi_result_filename", "kpi_results.xlsx"),
            getattr(self.ih, "selected_mf4_files", None),
        )

    def _detect_events(self):
        """Step 3: Run feature event detection if a segmenter is configured."""
        if self.SEGMENTER_CLS is None:
            print(f"\n➡️ [3/5] No event detection configured for {self.feature}; skipping.")
            return

        print(f"\n➡️ [3/5] Detecting {self.feature} events...")
        try:
            self.event = self.SEGMENTER_CLS(self.ih, self.cfg)
            print(f"🚦 Running {self.feature} event detection...\n")
            self.event.process_all_files()
            print(f"✅ {self.feature} event detection finished.\n")
        except Exception as exc:
            raise RuntimeError(f"❌ {self.feature} event detection failed: {exc}") from exc

    def _extract_kpis(self):
        """Step 4: Run configured event and cycle KPI extractors."""
        print(f"\n➡️ [4/5] Extracting {self.feature} KPIs...")
        try:
            if self.EVENT_EXTRACTOR_CLS is not None:
                event_kpi = self.EVENT_EXTRACTOR_CLS(self.cfg, self.event)
                event_kpi.process_mdf_events()
                event_kpi.export_event_kpis()
                self.kpi = event_kpi
                self.event_kpi = event_kpi

            if self.CYCLE_EXTRACTOR_CLS is not None:
                self.cycle_kpi = self.CYCLE_EXTRACTOR_CLS(self.ih, self.cfg)
                self.cycle_kpi.process_mdf_cycles()
                self.cycle_kpi.export_cycle_kpis()

            print(f"✅ {self.feature} KPI extraction and export done.")
        except Exception as exc:
            raise RuntimeError(f"❌ {self.feature} KPI extraction failed: {exc}") from exc

    def _visualize_results(self):
        """Step 5: Render configured event and cycle visualizations."""
        print(f"\n➡️ [5/5] Launching {self.feature} visualization...\n")
        try:
            if self.EVENT_VISUALIZER_CLS is not None and self.event_kpi is not None:
                self.viz = self.EVENT_VISUALIZER_CLS(self.cfg, self.event_kpi)
                self.viz.interactive = getattr(self, "default_interactive", False)
                self.viz.plot()

            if self._has_cycle_results():
                dashboard_feature = self.CYCLE_DASHBOARD_FEATURE or self.feature
                self.cycle_kpi.render_cycle_dashboards(feature_name=dashboard_feature)
        except Exception as exc:
            raise RuntimeError(f"❌ {self.feature} visualization failed: {exc}") from exc

    def _has_cycle_results(self):
        return (
            self.cycle_kpi is not None
            and getattr(self.cycle_kpi, "cycle_kpi_table", None) is not None
            and not self.cycle_kpi.cycle_kpi_table.empty
        )
