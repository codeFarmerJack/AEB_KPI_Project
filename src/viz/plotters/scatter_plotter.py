import numpy as np
import pandas as pd
import warnings

from src.viz.core.base_plotter import BasePlotter
from src.viz.core.figure_manager import FigureManager
from src.viz.core.style_manager import StyleManager
from src.viz.core.filter_manager import FilterManager
from src.viz.core.data_adapters import DataAdapters
from src.viz.core.layer_manager import LayerManager
from src.viz.core.exporters import Exporter


class ScatterPlotter(BasePlotter):
    """
    Responsibilities:
    - for each graph_spec row:
        * decide X/Y columns
        * filter rows
        * draw scatter/line
        * request layers (average + calibration)
        * ask Exporter to save HTML when done with a group
    """

    def __init__(self, visualizer):
        super().__init__(visualizer)

        self.graph_spec    = self.viz.graph_spec
        self.figure_mgr    = FigureManager()
        self.style_mgr     = StyleManager(self.viz.marker_shapes, self.viz.line_colors)
        self.filter_mgr    = FilterManager()
        self.layer_mgr     = LayerManager(self.viz.calibratables)
        self.exporter      = Exporter(self.viz.out_path_output)

        self._group_counter = getattr(self.viz, "_group_counter", iter(range(1, 200)))
        self.interactive    = getattr(self.viz, "interactive", False)

    # -------------------------------------------------------- #
    def plot_row(self, graph_idx: int) -> None:
        data = self.viz.kpi_data
        if not isinstance(data, pd.DataFrame) or data.empty:
            warnings.warn("⚠️ kpi_data is empty or invalid — cannot plot.")
            return

        title = self.graph_spec.loc[graph_idx, "title"]
        title = str(title)

        same_title_rows = self.graph_spec.index[
            self.graph_spec["title"] == title
        ].tolist()
        enabled_rows = [
            r
            for r in same_title_rows
            if self.filter_mgr.is_row_enabled(self.graph_spec.loc[r, "plotenabled"])
        ]

        if not enabled_rows:
            print(f"⚠️ Skipping '{title}' — no enabled rows.")
            return

        first_row, last_row = enabled_rows[0], enabled_rows[-1]
        is_first, is_last   = graph_idx == first_row, graph_idx == last_row

        # ---- create / reuse fig ----
        fig, ax, created = self.figure_mgr.get_or_create(title, self.graph_spec, is_new=is_first)
        if created:
            print(f"🆕 Created figure for '{title}'")
        else:
            print(f"🔁 Reusing figure for '{title}'")

        # ---- Y axis metadata ----
        y_var       = str(self.graph_spec.loc[graph_idx, "reference"])
        y_label     = str(self.graph_spec.loc[graph_idx, "axis_name"])
        legend_name = str(self.graph_spec.loc[graph_idx, "legend"])
        connect     = self._resolve_connect_flag(self.graph_spec.loc[graph_idx, "connectpoints"])
        avg_flag    = str(self.graph_spec.loc[graph_idx, "average"]).strip().lower() == "true"
        ax.set_ylabel(y_label.replace("_", " "))

        # first row sets y limits
        if is_first:
            try:
                y_min = float(self.graph_spec.loc[first_row, "min_axis_value"])
                y_max = float(self.graph_spec.loc[first_row, "max_axis_value"])
                ax.set_ylim(y_min, y_max)
            except Exception:
                pass

        # ---- choose marker + color ----
        row_in_group = same_title_rows.index(graph_idx)
        marker, color = self.style_mgr.get_marker_and_color(row_in_group)

        # ---- resolve X/Y columns ----
        x_var_global = str(self.graph_spec.loc[0, "reference"])
        x_col, y_col = DataAdapters.resolve_xy_columns(data, x_var_global, y_var)
        if not x_col or not y_col:
            return

        # ---- apply filter mask ----
        mask = self.filter_mgr.build_mask(
            data, self.graph_spec.loc[graph_idx, "plotenabled"]
        )
        x_vals    = data.loc[mask, x_col].to_numpy()
        y_vals    = DataAdapters.apply_reference_transform(
            y_var,
            data.loc[mask, y_col].to_numpy(),
        )
        if self._mask_zero_markers(title):
            nonzero_mask = np.isfinite(y_vals) & (y_vals != 0)
            x_vals = x_vals[nonzero_mask]
            y_vals = y_vals[nonzero_mask]

        # ---- draw series ----
        if connect:
            ax.plot(
                x_vals,
                y_vals,
                linestyle="-",
                marker=marker,
                color=color,
                label=legend_name,
            )
        else:
            ax.scatter(
                x_vals,
                y_vals,
                marker=marker,
                color=color,
                label=legend_name,
            )

        # record for legend ordering
        self.figure_mgr.add_label(title, legend_name)

        # ---- optional average line ----
        if avg_flag and len(y_vals) > 0:
            avg_label = self.layer_mgr.add_average_line(ax, legend_name, y_vals)
            if avg_label:
                self.figure_mgr.add_label(title, avg_label)
                print(f"➕ Added average line for '{legend_name}'.")

        # ---- if this is last row in group -> finalize + export ----
        if is_last:
            # add calibration curves for all enabled rows
            labels   = self.figure_mgr.get_labels(title)
            for row_idx in enabled_rows:
                cal_limit = str(self.graph_spec.loc[row_idx, "calibration_lim"]).strip()
                if cal_limit and cal_limit.lower() not in ["none", "nan", ""]:
                    cal_label = self.layer_mgr.add_calibration_limit(ax, cal_limit)
                    if cal_label:
                        labels.append(cal_label)

            group_id = next(self._group_counter)
            self.exporter.export_html(
                fig,
                title=title,
                group_id=group_id,
                draw_labels=labels,
                calibratables=self.viz.calibratables,
                interactive=self.interactive,
            )

            # cleanup local caches
            self.figure_mgr.close(title)

    # -------------------------------------------------------- #
    def _resolve_connect_flag(self, cp_raw):
        if isinstance(cp_raw, (bool, int, float)):
            return bool(cp_raw)
        return str(cp_raw).strip().lower() in ["true", "1", "yes", "y"]

    def _mask_zero_markers(self, title: str) -> bool:
        title_l = str(title).strip().lower()
        targets = (
            "brake jerk duration",
            "max brake jerk",
            "min brake jerk acceleration",
            "communication latency",
        )
        return any(t in title_l for t in targets)
