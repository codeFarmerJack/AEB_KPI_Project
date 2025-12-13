import warnings
import numpy as np
import pandas as pd

from src.viz.core.base_plotter import BasePlotter
from src.viz.core.figure_manager import FigureManager
from src.viz.core.style_manager import StyleManager
from src.viz.core.filter_manager import FilterManager
from src.viz.core.data_adapters import DataAdapters
from src.viz.core.layer_manager import LayerManager
from src.viz.core.exporters import Exporter


class BoxPlotter(BasePlotter):
    """
    Box-and-whisker plotting. Groups values by the X column when available.
    """

    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.graph_spec     = self.viz.graph_spec
        self.figure_mgr     = FigureManager()
        self.style_mgr      = StyleManager(self.viz.marker_shapes, self.viz.line_colors)
        self.filter_mgr     = FilterManager()
        self.layer_mgr      = LayerManager(self.viz.calibratables)
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
            print(f"🆕 Created BOX figure for '{title}'")

        y_var = str(self.graph_spec.loc[graph_idx, "reference"])
        y_label = str(self.graph_spec.loc[graph_idx, "axis_name"])
        legend_name = str(self.graph_spec.loc[graph_idx, "legend"])
        avg_flag = str(self.graph_spec.loc[graph_idx, "average"]).strip().lower() == "true"
        ax.set_ylabel(y_label.replace("_", " "))

        if is_first:
            try:
                y_min = float(self.graph_spec.loc[first_row, "min_axis_value"])
                y_max = float(self.graph_spec.loc[first_row, "max_axis_value"])
                ax.set_ylim(y_min, y_max)
            except Exception:
                pass

        x_var_global = str(self.graph_spec.loc[0, "reference"])
        x_col, y_col = DataAdapters.resolve_xy_columns(data, x_var_global, y_var)
        if not y_col:
            return

        mask = self.filter_mgr.build_mask(data, self.graph_spec.loc[graph_idx, "plotenabled"])
        plot_df = data.loc[mask]
        if plot_df.empty:
            warnings.warn(f"⚠️ No data to plot for '{legend_name}'.")
            return

        # Group by X if available; otherwise plot one box
        if x_col and x_col in plot_df.columns:
            grouped = plot_df.groupby(x_col)[y_col].apply(lambda s: s.dropna().to_numpy())
            labels = grouped.index.astype(str).tolist()
            series = [vals for vals in grouped if len(vals) > 0]
            if not series:
                warnings.warn(f"⚠️ No valid values found for '{legend_name}'.")
                return
            bp = ax.boxplot(series, labels=labels, patch_artist=True)
        else:
            vals = plot_df[y_col].dropna().to_numpy()
            if len(vals) == 0:
                warnings.warn(f"⚠️ No valid values found for '{legend_name}'.")
                return
            bp = ax.boxplot([vals], labels=[legend_name], patch_artist=True)

        # Color first box to match style palette for quick identification
        row_in_group = same_title_rows.index(graph_idx)
        _, color = self.style_mgr.get_marker_and_color(row_in_group)
        for box in bp.get("boxes", []):
            box.set_facecolor(color)
            box.set_alpha(0.5)

        for line in bp.get("medians", []):
            line.set_color("black")

        self.figure_mgr.add_label(title, legend_name)

        if avg_flag:
            vals = plot_df[y_col].to_numpy()
            avg_label = self.layer_mgr.add_average_line(ax, legend_name, vals)
            if avg_label:
                self.figure_mgr.add_label(title, avg_label)

        if is_last:
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
            self.figure_mgr.close(title)
