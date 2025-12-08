import warnings
import numpy as np
import pandas as pd

from src.viz.core.base_plotter import BasePlotter
from src.viz.core.figure_manager import FigureManager
from src.viz.core.filter_manager import FilterManager
from src.viz.core.data_adapters import DataAdapters
from src.viz.core.exporters import Exporter


class HeatmapPlotter(BasePlotter):
    """
    Basic 2D density heatmap using numpy.histogram2d.
    """

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.graph_spec     = self.viz.graph_spec
        self.figure_mgr     = FigureManager()
        self.filter_mgr     = FilterManager()
        self.exporter       = Exporter(self.viz.out_path_output)
        self._group_counter = getattr(self.viz, "_group_counter", iter(range(1, 200)))
        self.interactive    = getattr(self.viz, "interactive", False)

    def plot_row(self, graph_idx: int) -> None:
        data = self.viz.kpi_data
        if not isinstance(data, pd.DataFrame) or data.empty:
            warnings.warn("⚠️ kpi_data is empty or invalid — cannot plot.")
            return

        title = str(self.graph_spec.loc[graph_idx, "title"])
        same_title_rows = self.graph_spec.index[self.graph_spec["title"] == title].tolist()
        enabled_rows = [
            r for r in same_title_rows if self.filter_mgr.is_row_enabled(self.graph_spec.loc[r, "plotenabled"])
        ]
        if not enabled_rows:
            print(f"⚠️ Skipping '{title}' — no enabled rows.")
            return

        first_row, last_row = enabled_rows[0], enabled_rows[-1]
        is_first, is_last = graph_idx == first_row, graph_idx == last_row

        fig, ax, created = self.figure_mgr.get_or_create(title, self.graph_spec, is_new=is_first)
        if created:
            print(f"🆕 Created HEATMAP figure for '{title}'")

        y_var = str(self.graph_spec.loc[graph_idx, "reference"])
        y_label = str(self.graph_spec.loc[graph_idx, "axis_name"])
        ax.set_ylabel(y_label.replace("_", " "))

        x_var_global = str(self.graph_spec.loc[0, "reference"])
        x_col, y_col = DataAdapters.resolve_xy_columns(data, x_var_global, y_var)
        if not x_col or not y_col:
            return

        mask = self.filter_mgr.build_mask(data, self.graph_spec.loc[graph_idx, "plotenabled"])
        plot_df = data.loc[mask, [x_col, y_col]].dropna()
        if plot_df.empty:
            warnings.warn(f"⚠️ No data to plot for '{title}'.")
            return

        x_vals = plot_df[x_col].to_numpy(dtype=float)
        y_vals = plot_df[y_col].to_numpy(dtype=float)

        # Build a density grid
        heatmap, xedges, yedges = np.histogram2d(x_vals, y_vals, bins=50)
        extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
        img = ax.imshow(
            heatmap.T,
            extent=extent,
            origin="lower",
            aspect="auto",
            cmap="viridis",
        )
        fig.colorbar(img, ax=ax, label="Density")

        if is_last:
            labels   = self.figure_mgr.get_labels(title)
            group_id = next(self._group_counter)
            self.exporter.export_html(
                fig,
                title=title,
                group_id=group_id,
                draw_labels=labels,
                calibratables=self.viz.calibratables,
                interactive=self.interactive,
            )
            self.figure_mgr.close(title)
