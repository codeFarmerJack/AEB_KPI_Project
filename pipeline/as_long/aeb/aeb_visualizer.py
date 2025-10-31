import os
import warnings
import pandas as pd
from utils.viz.scatter_plotter import ScatterPlotter
from pipeline.as_long.base.base_visualizer import BaseVisualizer


class AebVisualizer(BaseVisualizer):
    """
    AebVisualizer — inherits BaseVisualizer but keeps its original plot() intact.
    """

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")

        # Keep existing attributes exactly as before
        self.graph_spec = self.filter_graph_spec()
        self._fig_cache = {}
        self._group_counter = iter(range(1, 101))
        print("🎯 AebVisualizer initialized (original plot() preserved).")

    # ------------------------------------------------------------------ #
    def plot(self):
        """Main dispatcher — loops through graph_spec rows."""
        if self.graph_spec is None or self.graph_spec.empty:
            warnings.warn("⚠️ No graph_spec found — skipping visualization.")
            return

        # Normalize column names
        self.graph_spec.columns = (
            self.graph_spec.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        # Drop "unnamed" columns (Excel leftovers)
        self.graph_spec = self.graph_spec.loc[:, ~self.graph_spec.columns.str.contains("^unnamed")]

        num_graphs = len(self.graph_spec)
        print(f"📊 Found {num_graphs} plot definitions in GraphSpec.")
        print("🎨 Launching visualization...\n")

        # Initialize the plotter here to reuse the same instance across all plots
        plotter = ScatterPlotter(self)
        
        for j in range(1, num_graphs):
            plot_type = str(self.graph_spec.loc[j, "plottype"]).strip().lower()
            title = str(self.graph_spec.loc[j, "title"]).strip()
            print(f"🎨 Plotting [{plot_type.upper()}] at row {j} — Title: {title}")

            try:
                if plot_type == "scatter":
                    plotter.plot(j)
                elif plot_type == "stem":
                    warnings.warn(f"⚙️ Stem plot at row {j} not yet implemented.")
                elif plot_type == "pie":
                    warnings.warn(f"⚙️ Pie plot at row {j} not yet implemented.")
                else:
                    warnings.warn(f"⚠️ Unsupported plot type '{plot_type}' at row {j}. Skipping.")
            except Exception as e:
                warnings.warn(f"⚠️ Plotting failed for row {j}: {e}")

        print("✅ Visualization complete.")