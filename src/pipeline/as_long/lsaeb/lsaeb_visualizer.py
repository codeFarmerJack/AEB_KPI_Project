import warnings
from src.utils.viz.scatter_plotter import ScatterPlotter
from src.pipeline.base.base_visualizer import BaseVisualizer


class LsaebVisualizer(BaseVisualizer):
    """LSAEB KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        # Initialize base visualizer with feature name "lsaeb"
        super().__init__(config, kpi_extractor, feature="lsaeb")

        self.graph_spec     = self.filter_graph_spec()
        self._fig_cache     = {}
        self._group_counter = iter(range(1, 101))
        print("🎯 LsaebVisualizer initialized.")

    # ------------------------------------------------------------------ #
    def plot(self):
        """Generate LSAEB KPI visualizations (scatter or other types)."""
        if self.graph_spec is None or self.graph_spec.empty:
            print("⚠️ No LSAEB plots defined in graphSpec.")
            return

        # --- Normalize column names ---
        self.graph_spec.columns = (
            self.graph_spec.columns.str.strip().str.lower().str.replace(" ", "_")
        )
        self.graph_spec = self.graph_spec.loc[
            :, ~self.graph_spec.columns.str.contains("^unnamed")
        ]

        num_graphs = len(self.graph_spec)
        print(f"📊 Found {num_graphs} LSAEB plot definitions.\n")

        # --- Initialize plotter (reuse for multiple plots) ---
        plotter = ScatterPlotter(self)

        # --- Iterate through each plot definition ---
        for j in range(1, num_graphs):
            plot_type = str(self.graph_spec.loc[j, "plottype"]).strip().lower()
            title = str(self.graph_spec.loc[j, "title"]).strip()

            print(f"🎨 [LSAEB] Plotting [{plot_type.upper()}] — {title}")
            try:
                if plot_type == "scatter":
                    plotter.plot(j)
                else:
                    warnings.warn(f"⚠️ Unsupported plot type '{plot_type}' for row {j}.")
            except Exception as e:
                warnings.warn(f"⚠️ LSAEB plot failed at row {j}: {e}")

        print("✅ LSAEB visualization complete.")
