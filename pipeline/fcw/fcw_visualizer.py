import warnings
from utils.viz.scatter_plotter import scatter_plotter
from pipeline.base.base_visualizer import BaseVisualizer


class FcwVisualizer(BaseVisualizer):
    """FCW KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="fcw")

        self.graph_spec = self.filter_graph_spec()
        self._fig_cache = {}
        self._group_counter = iter(range(1, 101))
        print("🎯 FcwVisualizer initialized.")

    def plot(self):
        """(Can be a clone of AebVisualizer.plot, or a simplified version.)"""
        if self.graph_spec.empty:
            print("⚠️ No FCW plots defined.")
            return

        self.graph_spec.columns = (
            self.graph_spec.columns.str.strip().str.lower().str.replace(" ", "_")
        )
        self.graph_spec = self.graph_spec.loc[:, ~self.graph_spec.columns.str.contains("^unnamed")]

        num_graphs = len(self.graph_spec)
        print(f"📊 Found {num_graphs} FCW plot definitions.\n")

        for j in range(1, num_graphs):
            plot_type = str(self.graph_spec.loc[j, "plottype"]).strip().lower()
            title = str(self.graph_spec.loc[j, "title"]).strip()
            print(f"🎨 [FCW] Plotting [{plot_type.upper()}] — {title}")
            try:
                if plot_type == "scatter":
                    scatter_plotter(self, j)
            except Exception as e:
                warnings.warn(f"⚠️ FCW plot failed at row {j}: {e}")

        print("✅ FCW visualization complete.")
