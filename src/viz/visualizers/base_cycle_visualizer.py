import html as html_lib
import os
import re
import warnings
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pyecharts import options as opts
from pyecharts.charts import Line, Grid
from pyecharts.commons.utils import JsCode

from src.utils.signal_mdf import safe_load_mdf, get_signal


class BaseCycleVisualizer:
    """
    Simple dashboard-style visualizer for cycle KPIs.
    Expects:
      - kpi_row: single-row Series or dict of KPI values
      - signals: dict-like with 'time', 'lon', 'lat', etc.
    """
    row_defs: list[dict] = []

    BASE_SIGNAL_CANDIDATES = {
        "time": ["time"],
        "lon": ["longitude"],
        "lat": ["latitude"],
        "speed": ["egoSpeedKph"],
    }
    DEFAULT_LAYOUT_PARAMS = {
        "rows": 2,
        "cols": 3,
        "shared_xaxes": False,
        "column_widths": [0.55, 0.10, 0.35],
        "row_heights": [0.6, 0.4],
        "horizontal_spacing": 0.13,
        "vertical_spacing": 0.05,
        "margins": {"l": 40, "r": 40, "t": 60, "b": 40},
        "specs": [
            [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
            [{"type": "xy", "colspan": 3}, None, None],
        ],
        "subplot_titles": (
            "Path (colored by speed)",
            "Availability",
            "Suppression Breakdown",
            "Signals",
        ),
    }
    DEFAULT_TOP_LAYOUT = {
        "rows": 1,
        "cols": 3,
        "column_widths": [0.45, 0.25, 0.30],
        "horizontal_spacing": 0.10,
        "vertical_spacing": 0.00,
        "margins": {"l": 20, "r": 20, "t": 2, "b": 8},
    }
    DEFAULT_TOP_TITLES = [
        "Path (colored by speed)",
        "Availability",
        "Suppression Breakdown",
    ]
    DEFAULT_AVAILABILITY_DEFS = [
        ("Availability", "AvailDistPct", "#4c6ef5"),
    ]
    DEFAULT_SUPPRESSION_PATTERNS = [
        "PedalPosProSuppression",
        "SteeringWheelAngle",
        "SteeringWheelAngleRate",
        "YawRate",
        "LatAccel",
        "LowSpeed",
    ]
    DEFAULT_SPEED_COLOR_RANGE = (0, 120)
    DEFAULT_SPEED_COLORBAR_TITLE = "Speed [kph]"
    DEFAULT_PATH_SMOOTHING = {
        "enabled": True,
        "sigma": 1.5,
        "min_points": 10,
    }
    DEFAULT_BOTTOM_CONFIG = {
        "bottom_row_height_px": 70,
        "bottom_row_gap_px": 16,
        "bottom_min_height_px": 650,
        "bottom_legend_pad_px": 12,
        "bottom_legend_item_gap": 0,
        "bottom_legend_gutter_px": 120,
        "bottom_legend_hidden_gutter_px": 24,
        "bottom_legend_left_pct": 88,
        "bottom_show_legend": False,
        "bottom_slider_height_px": 16,
        "bottom_slider_label_gap_px": 10,
        "bottom_slider_margin_px": 6,
        "bottom_round_decimals": 2,
        "bottom_max_points": 5000,
        "bottom_cursor_panel_width_px": 400,
        "bottom_cursor_panel_gap_px": 12,
        "bottom_cursor_time_decimals": 3,
        "bottom_cursor_value_decimals": None,
        "bottom_cursor_signal_col_width_px": 140,
        "bottom_cursor_value_col_width_px": 50,
        "bottom_cursor_unit_col_width_px": 40,
        "bottom_cursor_color_a": "#f06595",
        "bottom_cursor_color_b": "#845ef7",
        "bottom_cursor_line_width": 1,
    }

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        self.signal_candidates = self._build_signal_candidates_from_rows()
        self.layout_params = dict(
            getattr(self, "layout_params", None) or self.DEFAULT_LAYOUT_PARAMS
        )
        self.layout_top = dict(getattr(self, "layout_top", None) or self.DEFAULT_TOP_LAYOUT)
        self.fig_top_titles = list(getattr(self, "fig_top_titles", None) or self.DEFAULT_TOP_TITLES)
        self.availability_defs = list(
            getattr(self, "availability_defs", None) or self.DEFAULT_AVAILABILITY_DEFS
        )
        self.suppression_patterns = list(
            getattr(self, "suppression_patterns", None) or self.DEFAULT_SUPPRESSION_PATTERNS
        )
        self.state_defs = list(getattr(self, "state_defs", None) or [])
        self.state_colors = dict(getattr(self, "state_colors", None) or {})
        self.default_state_color = getattr(self, "default_state_color", "#adb5bd")
        self.path_smoothing = dict(
            getattr(self, "path_smoothing", None) or self.DEFAULT_PATH_SMOOTHING
        )
        self.speed_color_range = getattr(self, "speed_color_range", None) or self.DEFAULT_SPEED_COLOR_RANGE
        self.speed_colorbar_title = getattr(
            self,
            "speed_colorbar_title",
            self.DEFAULT_SPEED_COLORBAR_TITLE,
        )
        self._init_bottom_config()

    # ------------------------------------------------------------------ #
    # Overridable hooks
    # ------------------------------------------------------------------ #
    def get_layout_params(self):
        """
        Return kwargs for plotly.subplots.make_subplots.
        Subclasses can override to change layout (num_rows/num_cols/sizes/titles).
        """
        return dict(self.layout_params)

    def prepare_signals(self, signals: dict) -> dict:
        """
        Hook to tweak/augment signals before plotting.
        Subclasses can override (e.g., unit conversion, custom keys).
        """
        return signals or {}

    def extract_cycle_signals(self, mdf):
        """
        Default signal extraction for cycle dashboards.
        Subclasses can override for feature-specific signals.
        """
        def pick(candidates):
            for c in candidates:
                try:
                    val = get_signal(mdf, c)
                    if val is not None:
                        return val
                except Exception:
                    continue
            return None

        candidates = self.signal_candidates

        return {key: pick(vals) for key, vals in candidates.items()}

    def _init_bottom_config(self):
        for key, default in self.DEFAULT_BOTTOM_CONFIG.items():
            setattr(self, key, getattr(self, key, default))

    def _collect_availability_values(self, kpi_row):
        labels = []
        values = []
        colors = []
        for label, key, color in self.availability_defs:
            val = kpi_row.get(key)
            if val is None:
                continue
            labels.append(label)
            values.append(val)
            colors.append(color)
        return labels, values, colors

    def _collect_suppression_values(self, kpi_row):
        reason_keys = [p for p in self.suppression_patterns if p in kpi_row]
        values = [kpi_row.get(k, 0) for k in reason_keys]
        return reason_keys, values

    def _smooth_path(self, lon_arr, lat_arr):
        smoothing = self.path_smoothing or {}
        enabled = smoothing.get("enabled", True)
        min_points = smoothing.get("min_points", 10)
        sigma = smoothing.get("sigma", 1.5)

        if not enabled:
            return lon_arr, lat_arr
        if len(lon_arr) <= min_points:
            return lon_arr, lat_arr
        if not (np.isfinite(lon_arr).any() and np.isfinite(lat_arr).any()):
            return lon_arr, lat_arr
        try:
            from scipy.ndimage import gaussian_filter1d
        except Exception:
            return lon_arr, lat_arr

        return gaussian_filter1d(lon_arr, sigma=sigma), gaussian_filter1d(lat_arr, sigma=sigma)

    def _add_state_overlays(self, fig, lon_to_plot, lat_to_plot, signals):
        if not self.state_defs:
            return
        seen_legend = set()
        for state_def in self.state_defs:
            signal_name = state_def.get("signal_name")
            if not signal_name:
                continue
            state_values = signals.get(signal_name)
            if state_values is None:
                continue
            label_prefix = state_def.get("label_prefix", signal_name)
            state_names = self._decode_state_names(signal_name, state_values)
            self._add_state_segments(
                fig,
                lon_to_plot,
                lat_to_plot,
                state_names,
                label_prefix,
                row=1,
                col=1,
                color_map=self.state_colors,
                default_color=self.default_state_color,
                seen_legend=seen_legend,
            )

    def _plot_path_state(self, fig, signals, row, col, signal_name, label_prefix=None,
                         legend_id=None):
        lon = signals.get("lon")
        lat = signals.get("lat")
        if lon is None or lat is None:
            return False

        lon_arr = np.asarray(lon, dtype=float)
        lat_arr = np.asarray(lat, dtype=float)

        lon_to_plot, lat_to_plot = self._smooth_path(lon_arr, lat_arr)
        seen_legend = set()
        state_values = signals.get(signal_name)
        label_prefix = label_prefix or signal_name
        if state_values is not None:
            state_names = self._decode_state_names(signal_name, state_values)
            self._add_state_segments(
                fig,
                lon_to_plot,
                lat_to_plot,
                state_names,
                label_prefix,
                row=row,
                col=col,
                color_map=self.state_colors,
                default_color=self.default_state_color,
                seen_legend=seen_legend,
                legend_id=legend_id,
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=lon_to_plot,
                    y=lat_to_plot,
                    mode="lines",
                    line=dict(width=3, color=self.default_state_color),
                    connectgaps=True,
                    showlegend=False,
                ),
                row=row,
                col=col,
            )
        return True

    def _add_path_subplot(self, fig, signals, row=1, col=1,
                          path_state_signal=None, path_label_prefix=None):
        lon = signals.get("lon")
        lat = signals.get("lat")
        if lon is None or lat is None:
            return None

        path_state_signal = (
            path_state_signal
            if path_state_signal is not None
            else getattr(self, "path_color_signal", None)
        )
        if path_state_signal:
            label_prefix = path_label_prefix
            if label_prefix is None:
                label_prefix = getattr(self, "path_color_label_prefix", path_state_signal)
            return self._plot_path_state(
                fig,
                signals,
                row=row,
                col=col,
                signal_name=path_state_signal,
                label_prefix=label_prefix,
            )

        lon_arr = np.asarray(lon, dtype=float)
        lat_arr = np.asarray(lat, dtype=float)
        lon_to_plot, lat_to_plot = self._smooth_path(lon_arr, lat_arr)

        spd = signals.get("speed")
        if spd is None:
            return None
        spd_arr = np.asarray(spd, dtype=float)
        fig.add_trace(
            go.Scatter(
                x=lon_to_plot,
                y=lat_to_plot,
                mode="lines+markers",
                marker=dict(size=3, color=spd_arr, coloraxis="coloraxis"),
                line=dict(width=3, color="rgba(0,0,0,0.1)"),
                connectgaps=True,
                showlegend=False,
            ),
            row=row,
            col=col,
        )
        self._add_state_overlays(fig, lon_to_plot, lat_to_plot, signals)
        self._path_uses_speed_color = True
        return True

    def _apply_speed_colorbar(self, fig, xaxis_key="xaxis", yaxis_key="yaxis"):
        xaxis = getattr(fig.layout, xaxis_key, None)
        yaxis = getattr(fig.layout, yaxis_key, None)
        if xaxis is None or yaxis is None:
            return
        x0, x1 = xaxis.domain
        y0, y1 = yaxis.domain
        colorbar_x = x1
        colorbar_len = 1.1 * (y1 - y0)
        colorbar_y = (y0 + y1) / 2
        cmin, cmax = self.speed_color_range
        fig.update_layout(
            coloraxis=dict(
                colorscale="Turbo",
                cmin=cmin,
                cmax=cmax,
                colorbar=dict(
                    title=dict(text=self.speed_colorbar_title, side="right"),
                    x=colorbar_x,
                    y=colorbar_y,
                    len=colorbar_len,
                    lenmode="fraction",
                    thickness=20,
                    outlinewidth=0,
                ),
            ),
        )

    def _decode_state_names(self, signal_name, values):
        if values is None:
            return None
        names = []
        for v in np.asarray(values):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                names.append(None)
                continue
            if isinstance(v, str):
                names.append(v)
                continue
            try:
                names.append(str(int(v)))
            except Exception:
                names.append(None)
        return names

    def _format_state_label(self, state_name):
        if not state_name:
            return "Unknown"
        prefixes = (
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_",
            "FORWARD_COLLISION_WARNING_PLANNER_STATE_",
        )
        label = state_name
        for prefix in prefixes:
            if label.startswith(prefix):
                label = label[len(prefix):]
                break
        return label.replace("_", " ").title()

    def _add_state_segments(self, fig, x, y, state_names, label_prefix, row, col,
                            color_map, default_color, seen_legend=None, legend_id=None):
        if x is None or y is None or state_names is None:
            return
        x_arr = np.asarray(x)
        y_arr = np.asarray(y)
        n = min(len(x_arr), len(y_arr))
        if n == 0:
            return
        x_arr = x_arr[:n]
        y_arr = y_arr[:n]
        names = list(state_names)
        if not names:
            names = ["Unknown"] * n
        elif len(names) < n:
            last = next((name for name in reversed(names) if name), None)
            fill = last if last else "Unknown"
            names.extend([fill] * (n - len(names)))
        else:
            names = names[:n]

        last_name = None
        for idx, name in enumerate(names):
            if name is None:
                names[idx] = last_name if last_name else "Unknown"
            else:
                last_name = name
        i = 0
        while i < n - 1:
            name = names[i]
            j = i + 1
            while j < n and names[j] == name:
                j += 1
            end = min(j + 1, n)
            color = color_map.get(name, default_color)
            legend_name = f"{label_prefix}: {self._format_state_label(name)}"
            showlegend = True
            if seen_legend is not None:
                showlegend = legend_name not in seen_legend
                if showlegend:
                    seen_legend.add(legend_name)
            fig.add_trace(
                go.Scatter(
                    x=x_arr[i:end],
                    y=y_arr[i:end],
                    mode="lines",
                    line=dict(width=2, color=color),
                    name=legend_name,
                    legend=legend_id,
                    showlegend=showlegend,
                    connectgaps=True,
                    text=[name] * (end - i),
                    hovertemplate=f"{label_prefix}<br>%{{text}}<extra></extra>",
                ),
                row=row,
                col=col,
            )
            i = j

    def _build_signal_candidates_from_rows(self) -> dict:
        """
        Build signal_candidates automatically from row_defs.
        """
        candidates = dict(self.BASE_SIGNAL_CANDIDATES)

        for row in self.row_defs:
            for series in row["series"]:
                signal_key, _, _, _series_opts = self._parse_series_def(series)
                candidates.setdefault(signal_key, [signal_key])

        return candidates

    def _build_fig_top(self, kpi_row, signals):
        lt = self.layout_top or self.DEFAULT_TOP_LAYOUT
        path_subplot_defs = getattr(self, "path_subplot_defs", None) or [{"row": 1, "col": 1}]
        layout_top = dict(lt)
        path_cols = sorted(
            {
                path_def.get("col", 1)
                for path_def in path_subplot_defs
                if path_def.get("signal_name")
            }
        )
        column_widths = layout_top.get("column_widths")
        if column_widths:
            if len(path_cols) >= 2:
                shrink_factor = getattr(self, "path_col_shrink_factor", 0.8)
                adjusted = list(column_widths)
                for col in path_cols:
                    idx = col - 1
                    if 0 <= idx < len(adjusted):
                        adjusted[idx] *= shrink_factor
                layout_top["column_widths"] = adjusted
        if len(path_cols) <= 1:
            spacing = getattr(self, "single_path_horizontal_spacing", None)
            if spacing is None:
                spacing = layout_top.get("horizontal_spacing")
                if spacing is not None:
                    spacing = min(spacing, 0.06)
            if spacing is not None:
                layout_top["horizontal_spacing"] = spacing
        subplot_titles = self.fig_top_titles or self.DEFAULT_TOP_TITLES

        fig_top = make_subplots(
            rows=layout_top["rows"],
            cols=layout_top["cols"],
            subplot_titles=subplot_titles,
            horizontal_spacing=layout_top["horizontal_spacing"],
            vertical_spacing=layout_top["vertical_spacing"],
            column_widths=layout_top["column_widths"],
        )

        fig_top.update_layout(margin=layout_top["margins"])

        self._path_uses_speed_color = False
        path_added = False
        path_legends = []
        legend_idx = 0
        for path_def in path_subplot_defs:
            row = path_def.get("row", 1)
            col = path_def.get("col", 1)
            signal_name = path_def.get("signal_name")
            label_prefix = path_def.get("label_prefix")
            if signal_name:
                legend_idx += 1
                legend_id = path_def.get("legend_id")
                if not legend_id:
                    legend_id = "legend" if legend_idx == 1 else f"legend{legend_idx}"
                added = self._plot_path_state(
                    fig_top,
                    signals,
                    row=row,
                    col=col,
                    signal_name=signal_name,
                    label_prefix=label_prefix,
                    legend_id=legend_id,
                )
            else:
                legend_id = None
                added = self._add_path_subplot(
                    fig_top,
                    signals,
                    row=row,
                    col=col,
                    path_state_signal=None,
                    path_label_prefix=None,
                )
            if added:
                path_added = True
                if legend_id:
                    path_legends.append((legend_id, row, col))
                fig_top.update_yaxes(scaleanchor="x", row=row, col=col)

        # Subplot(1, 2) - Availability (Feature / ROV / VAL)
        availability_row = getattr(self, "availability_row", 1)
        availability_col = getattr(self, "availability_col", 2)
        labels, values, colors = self._collect_availability_values(kpi_row)

        if labels:
            fig_top.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    marker_color=colors,
                    text=[f"{v:.1f}%" for v in values],
                    textposition="inside",
                    showlegend=False,
                ),
                row=availability_row,
                col=availability_col,
            )
            fig_top.update_yaxes(
                range=[0, 100],
                title_text="Percent [%]",
                title_standoff=5,
                row=availability_row,
                col=availability_col,
            )

        # Subplot(1, 3) - Suppression breakdown
        suppression_row = getattr(self, "suppression_row", 1)
        suppression_col = getattr(self, "suppression_col", 3)
        reason_keys, values = self._collect_suppression_values(kpi_row)
        if reason_keys:
            fig_top.add_trace(
                go.Bar(
                    x=values,
                    y=reason_keys,
                    orientation="h",
                    marker_color="#74c0fc",
                    text=[f"{v:.1f}%" for v in values],
                    textposition="inside",
                    showlegend=False,
                ),
                row=suppression_row,
                col=suppression_col,
            )

        fig_top.update_yaxes(
            autorange="reversed",
            tickangle=-45,
            row=suppression_row,
            col=suppression_col,
        )
        fig_top.update_xaxes(
            range=[0, 100],
            title_text="Percent [%]",
            title_standoff=5,
            row=suppression_row,
            col=suppression_col,
        )

        fig_top.update_layout(
            height=400,
            margin=dict(l=40, r=40, t=60, b=20),
            template="plotly_white",
            showlegend=True,
            barmode="group",
        )
        if path_legends:
            legend_pad_x = getattr(self, "path_legend_pad_x", 0.015)
            legend_pad_y = getattr(self, "path_legend_pad_y", 0.015)
            legend_layout = {}
            cols = layout_top.get("cols", 1)
            for legend_id, row, col in path_legends:
                axis_index = (row - 1) * cols + col
                xaxis_key = "xaxis" if axis_index == 1 else f"xaxis{axis_index}"
                yaxis_key = "yaxis" if axis_index == 1 else f"yaxis{axis_index}"
                xaxis = getattr(fig_top.layout, xaxis_key, None)
                yaxis = getattr(fig_top.layout, yaxis_key, None)
                if xaxis is not None and yaxis is not None:
                    x0, x1 = xaxis.domain
                    y0, y1 = yaxis.domain
                    legend_x = x0 + legend_pad_x
                    legend_y = y1 - legend_pad_y
                else:
                    legend_x = 0.0
                    legend_y = 1.0
                legend_layout[legend_id] = dict(
                    orientation="v",
                    xanchor="left",
                    yanchor="top",
                    x=legend_x,
                    y=legend_y,
                    font=dict(size=10),
                )
            fig_top.update_layout(**legend_layout)
        if path_added and getattr(self, "_path_uses_speed_color", False):
            self._apply_speed_colorbar(fig_top, xaxis_key="xaxis", yaxis_key="yaxis")

        return fig_top

    def _build_fig_bottom(self, signals: dict):
        if not self.row_defs:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define row_defs"
            )

        self._bottom_series_meta = []

        time_arr = signals.get("time")
        if time_arr is None:
            raise ValueError("Missing 'time' signal")
        x_full = np.asarray(time_arr, dtype=float).tolist()
        x_indices = self._downsample_indices(len(x_full), self.bottom_max_points)
        x = self._apply_indices(x_full, x_indices)
        x_len = len(x_full)

        # === build active_rows from self.row_defs ===
        active_rows = []
        for row in self.row_defs:
            series_data = []
            for series in row["series"]:
                key, color, label, series_opts = self._parse_series_def(series)
                data = signals.get(key)
                if data is None:
                    continue
                y_vals = self._to_float_list(data)
                y_vals = self._format_series(
                    y_vals,
                    series_opts.get("round", self.bottom_round_decimals),
                    series_opts.get("cast"),
                )
                y_vals = self._align_series_length(y_vals, x_len)
                y_vals = self._apply_indices(y_vals, x_indices)
                series_data.append(
                    {
                        "label": label,
                        "color": color,
                        "y": y_vals,
                    }
                )

            if series_data:
                active_rows.append(
                    {
                        **row,
                        "series": series_data,
                    }
                )

        if not active_rows:
            return Grid()

        row_gap_px = self.bottom_row_gap_px
        show_legend = bool(self.bottom_show_legend)
        legend_pad_px = self.bottom_legend_pad_px if show_legend else 0
        legend_gutter_px = (
            self.bottom_legend_gutter_px
            if show_legend
            else self.bottom_legend_hidden_gutter_px
        )
        slider_space_px = (
            self.bottom_slider_height_px
            + self.bottom_slider_label_gap_px
            + self.bottom_slider_margin_px
        )

        for row in active_rows:
            row["height_px"] = row.get("height_px", self.bottom_row_height_px)

        rows_total_px = sum(row["height_px"] for row in active_rows)
        grid_height = max(
            self.bottom_min_height_px,
            int(
                rows_total_px + (len(active_rows) - 1) * row_gap_px
                + slider_space_px
            ),
        )
        grid = Grid(
            init_opts=opts.InitOpts(
                width="100%",
                height=f"{grid_height}px",
                bg_color="#ffffff",
            )
        )

        row_gap = row_gap_px / grid_height * 100
        slider_space = slider_space_px / grid_height * 100
        legend_pad = legend_pad_px / grid_height * 100
        slider_bottom_pct = (self.bottom_slider_margin_px / grid_height) * 100
        scale = (100 - slider_space - (len(active_rows) - 1) * row_gap) / max(
            rows_total_px,
            1,
        )

        xaxis_indices = list(range(len(active_rows)))
        axis_pointer = opts.AxisPointerOpts(
            is_show=True,
            link=[{"xAxisIndex": "all"}],
            is_snap=True,
            is_trigger_tooltip=True,
            label=opts.LabelOpts(is_show=False),
        )
        tooltip = opts.TooltipOpts(
            trigger="axis",
            axis_pointer_type="line",
            is_show_content=False,
            formatter=JsCode("function () { return ''; }"),
            background_color="rgba(0,0,0,0)",
            border_width=0,
            padding=0,
            extra_css_text="box-shadow:none;",
        )
        label_decimals = (
            int(self.bottom_round_decimals)
            if self.bottom_round_decimals is not None
            else 3
        )
        value_label = opts.LabelOpts(
            is_show=True,
            position="inside",
            distance=0,
            color="#000000",
            formatter=JsCode(
                f"""
                function (params) {{
                    var d = params.data;
                    var v = d;
                    if (d && typeof d === 'object') {{
                        if (d.name !== undefined && d.name !== null && d.name !== '') {{
                            v = d.name;
                        }} else if (d.value !== undefined) {{
                            v = d.value;
                        }}
                    }}
                    if (Array.isArray(v)) {{
                        v = v[v.length - 1];
                    }}
                    if (typeof v === 'number' && isFinite(v)) {{
                        v = v.toFixed({label_decimals});
                    }}
                    return v;
                }}
                """
            ),
        )

        top_pct = 0.0

        for idx, row in enumerate(active_rows):
            line = Line().add_xaxis(xaxis_data=x)

            for series in row["series"]:
                line = line.add_yaxis(
                    series_name=series["label"],
                    y_axis=series["y"],
                    is_symbol_show=False,
                    symbol="none",
                    symbol_size=0,
                    label_opts=opts.LabelOpts(is_show=False),
                    emphasis_opts=opts.EmphasisOpts(label_opts=value_label),
                    linestyle_opts=opts.LineStyleOpts(color=series["color"]),
                    itemstyle_opts=opts.ItemStyleOpts(color=series["color"]),
                )
                self._bottom_series_meta.append(
                    {
                        "label": series["label"],
                        "unit": row.get("unit") or "",
                        "color": series["color"],
                    }
                )

            y_min, y_max = None, None
            if row.get("y_range"):
                y_min, y_max = row["y_range"]

            row_height = row["height_px"] * scale
            plot_height = max(row_height - legend_pad, 1)

            legend_orient = "vertical" if len(row["series"]) > 1 else "horizontal"
            legend_opts = opts.LegendOpts(
                is_show=show_legend,
                orient=legend_orient,
                pos_left=f"{self.bottom_legend_left_pct}%",
                pos_top=f"{top_pct + 0.1}%",
                align="left",
                item_gap=self.bottom_legend_item_gap,
                item_width=28,
                item_height=2,
                legend_icon="rect",
                textstyle_opts=opts.TextStyleOpts(font_size=10),
            )

            yaxis_kwargs = {
                "axispointer_opts": opts.AxisPointerOpts(
                    is_show=False,
                    label=opts.LabelOpts(is_show=False),
                ),
                "split_number": 2,
            }
            unit = row.get("unit")

            if y_min is not None and y_max is not None:
                yaxis_kwargs.update(min_=y_min, max_=y_max)
                if (y_max - y_min) < 2:
                    yaxis_kwargs["split_number"] = 1

            datazoom = opts.DataZoomOpts(
                type_="slider",
                xaxis_index=xaxis_indices,
                pos_bottom=f"{slider_bottom_pct:.2f}%",
                is_show_data_shadow=False,
                is_show_detail=False,
                range_start=0,
                range_end=100,
            )
            datazoom.opts["height"] = self.bottom_slider_height_px

            line = line.set_global_opts(
                tooltip_opts=tooltip,
                xaxis_opts=opts.AxisOpts(
                    type_="value",
                    axislabel_opts=opts.LabelOpts(
                        is_show=(idx == len(active_rows) - 1)
                    ),
                    axispointer_opts=opts.AxisPointerOpts(
                        is_show=True,
                        label=opts.LabelOpts(is_show=False),
                    ),
                ),
                yaxis_opts=opts.AxisOpts(**yaxis_kwargs),
                legend_opts=legend_opts,
                axispointer_opts=axis_pointer,
                datazoom_opts=(
                    [datazoom]
                    if idx == len(active_rows) - 1
                    else None
                ),
            )

            grid.add(
                line,
                grid_opts=opts.GridOpts(
                    pos_left="80px",
                    pos_right=f"{legend_gutter_px}px",
                    pos_top=f"{top_pct + legend_pad}%",
                    height=f"{plot_height}%",
                ),
            )

            top_pct += row_height + row_gap

        return grid

    def _cursor_panel_css(self) -> str:
        panel_width = int(self.bottom_cursor_panel_width_px)
        panel_gap = int(self.bottom_cursor_panel_gap_px)
        signal_col_width = int(self.bottom_cursor_signal_col_width_px)
        value_col_width = int(self.bottom_cursor_value_col_width_px)
        unit_col_width = int(self.bottom_cursor_unit_col_width_px)
        return f"""
        .cycle-bottom-wrap {{
            display: flex;
            align-items: stretch;
            gap: {panel_gap}px;
        }}
        .cycle-bottom-chart {{
            flex: 1 1 auto;
            min-width: 0;
        }}
        .cycle-cursor-panel {{
            width: {panel_width}px;
            min-width: {panel_width}px;
            max-width: {panel_width}px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 8px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            gap: 6px;
            font-size: 12px;
            color: #212529;
        }}
        .cycle-cursor-title {{
            font-weight: 600;
            font-size: 12px;
        }}
        .cycle-cursor-summary {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2px;
            font-size: 11px;
        }}
        .cycle-cursor-summary span {{
            font-weight: 600;
        }}
        .cycle-cursor-table-wrap {{
            flex: 1 1 auto;
            overflow-y: auto;
            overflow-x: auto;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            background: #ffffff;
        }}
        .cycle-cursor-table {{
            width: max-content;
            min-width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            font-size: 11px;
        }}
        .cycle-cursor-table th,
        .cycle-cursor-table td {{
            padding: 2px 4px;
            border-bottom: 1px solid #f1f3f5;
            text-align: right;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .cycle-cursor-table th:first-child,
        .cycle-cursor-table td:first-child {{
            text-align: left;
            width: {signal_col_width}px;
            max-width: {signal_col_width}px;
            min-width: {signal_col_width}px;
        }}
        .cycle-cursor-table th:nth-child(2),
        .cycle-cursor-table td:nth-child(2),
        .cycle-cursor-table th:nth-child(3),
        .cycle-cursor-table td:nth-child(3),
        .cycle-cursor-table th:nth-child(4),
        .cycle-cursor-table td:nth-child(4) {{
            width: {value_col_width}px;
            max-width: {value_col_width}px;
            min-width: {value_col_width}px;
        }}
        .cycle-cursor-table th:nth-child(5),
        .cycle-cursor-table td:nth-child(5) {{
            width: {unit_col_width}px;
            max-width: {unit_col_width}px;
            min-width: {unit_col_width}px;
        }}
        .cycle-signal-cell {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .cycle-signal-swatch {{
            width: 16px;
            height: 3px;
            border-radius: 2px;
            flex: 0 0 auto;
        }}
        .cycle-cursor-table th {{
            position: sticky;
            top: 0;
            background: #f1f3f5;
            z-index: 1;
            font-weight: 600;
        }}
        .cycle-cursor-hint {{
            font-size: 10px;
            color: #868e96;
        }}
        """

    def _build_cursor_panel_html(self, chart_id: str) -> str:
        rows = []
        series_meta = getattr(self, "_bottom_series_meta", [])
        for idx, meta in enumerate(series_meta):
            label = html_lib.escape(str(meta.get("label", "")))
            unit = html_lib.escape(str(meta.get("unit", "")))
            color = html_lib.escape(str(meta.get("color", "#adb5bd")))
            rows.append(
                f"""
                <tr data-series-index="{idx}">
                  <td>
                    <div class="cycle-signal-cell">
                      <span class="cycle-signal-swatch" style="background:{color};"></span>
                      <span>{label}</span>
                    </div>
                  </td>
                  <td class="cursor-val-a">--</td>
                  <td class="cursor-val-b">--</td>
                  <td class="cursor-val-diff">--</td>
                  <td class="cursor-unit">{unit}</td>
                </tr>
                """
            )
        rows_html = "\n".join(rows)
        return f"""
        <div class="cycle-cursor-panel" id="cursor-panel-{chart_id}">
          <div class="cycle-cursor-title">Cursor Values</div>
          <div class="cycle-cursor-summary">
            <div>Cursor A: <span id="cursor-a-{chart_id}">--</span> s</div>
            <div>Cursor B: <span id="cursor-b-{chart_id}">--</span> s</div>
            <div>Delta: <span id="cursor-delta-{chart_id}">--</span> s</div>
          </div>
          <div class="cycle-cursor-table-wrap">
            <table class="cycle-cursor-table">
              <thead>
                <tr>
                  <th>Signal</th>
                  <th>Val1</th>
                  <th>Val2</th>
                  <th>Diff</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody id="cursor-body-{chart_id}">
                {rows_html}
              </tbody>
            </table>
          </div>
          <div class="cycle-cursor-hint">Click to set A then B, Shift+click to set B</div>
        </div>
        """

    @staticmethod
    def _inject_before_body_end(html: str, extra: str) -> str:
        marker = "</body>"
        if marker in html:
            return html.replace(marker, f"{extra}\n{marker}", 1)
        return html + extra

    def _wrap_bottom_html(self, html: str, chart_id: str, panel_html: str) -> str:
        pattern = rf'(<div id="{re.escape(chart_id)}"[^>]*></div>)'
        match = re.search(pattern, html)
        if not match:
            return html + panel_html
        chart_div = match.group(1)
        wrapped = (
            f'<div class="cycle-bottom-wrap" id="cycle-wrap-{chart_id}">'
            f'<div class="cycle-bottom-chart">{chart_div}</div>'
            f'{panel_html}'
            f"</div>"
        )
        return html.replace(chart_div, wrapped, 1)

    def _build_cursor_panel_script(self, chart_id: str) -> str:
        time_decimals = (
            int(self.bottom_cursor_time_decimals)
            if self.bottom_cursor_time_decimals is not None
            else 3
        )
        value_decimals = self.bottom_cursor_value_decimals
        if value_decimals is None:
            value_decimals = self.bottom_round_decimals
        if value_decimals is None:
            value_decimals = 3
        value_decimals = int(value_decimals)
        color_a = self.bottom_cursor_color_a
        color_b = self.bottom_cursor_color_b
        line_width = int(self.bottom_cursor_line_width)
        return f"""
        <script>
        (function() {{
          var chartId = "{chart_id}";
          var chartEl = document.getElementById(chartId);
          if (!chartEl || !window.echarts) {{
            return;
          }}
          var chart = echarts.getInstanceByDom(chartEl);
          if (!chart) {{
            setTimeout(function () {{
              var retry = echarts.getInstanceByDom(chartEl);
              if (retry && !retry.__cursorPanelAttached) {{
                retry.__cursorPanelAttached = true;
                init(retry);
              }}
            }}, 100);
            return;
          }}
          if (chart.__cursorPanelAttached) {{
            return;
          }}
          chart.__cursorPanelAttached = true;
          init(chart);

          function init(chart) {{
            var option = chart.getOption();
            var seriesList = option.series || [];
            if (!seriesList.length) {{
              return;
            }}

          function extractX(series) {{
            var data = series.data || [];
            if (!data.length) {{
              return [];
            }}
            var first = data[0];
            if (Array.isArray(first)) {{
              return data.map(function (d) {{
                return Array.isArray(d) ? d[0] : null;
              }});
            }}
            if (first && typeof first === "object" && Array.isArray(first.value)) {{
              return data.map(function (d) {{
                return d && Array.isArray(d.value) ? d.value[0] : null;
              }});
            }}
            var xAxisIdx = series.xAxisIndex || 0;
            var xAxis = option.xAxis || [];
            if (Array.isArray(xAxis) && xAxis[xAxisIdx] && xAxis[xAxisIdx].data) {{
              return xAxis[xAxisIdx].data;
            }}
            return [];
          }}

          function getSeriesValue(series, idx) {{
            var data = series.data || [];
            if (idx == null || idx < 0 || idx >= data.length) {{
              return null;
            }}
            var point = data[idx];
            if (Array.isArray(point)) {{
              return point[1];
            }}
            if (point && typeof point === "object") {{
              if (Array.isArray(point.value)) {{
                return point.value[1];
              }}
              if (point.value !== undefined) {{
                return point.value;
              }}
            }}
            return null;
          }}

          function formatValue(val, decimals) {{
            if (val === null || val === undefined || val === "") {{
              return "--";
            }}
            if (typeof val === "number") {{
              if (!isFinite(val)) {{
                return "--";
              }}
              if (Math.abs(val - Math.round(val)) < 1e-9) {{
                return String(Math.round(val));
              }}
              return val.toFixed(decimals);
            }}
            return String(val);
          }}

          function findNearestIndex(list, value) {{
            if (!list || !list.length) {{
              return null;
            }}
            var bestIdx = null;
            var bestDiff = Infinity;
            for (var i = 0; i < list.length; i++) {{
              var v = list[i];
              if (v === null || v === undefined || !isFinite(v)) {{
                continue;
              }}
              var diff = Math.abs(v - value);
              if (diff < bestDiff) {{
                bestDiff = diff;
                bestIdx = i;
              }}
            }}
            return bestIdx;
          }}

          function pickBaseSeries(list) {{
            for (var i = 0; i < list.length; i++) {{
              if (list[i] && list[i].data && list[i].data.length) {{
                return list[i];
              }}
            }}
            return list[0];
          }}

          var xList = extractX(pickBaseSeries(seriesList));
          var cursorA = null;
          var cursorB = null;

          function updateMarkLines() {{
            var lineData = [];
            if (cursorA !== null) {{
              lineData.push({{
                xAxis: cursorA.x,
                lineStyle: {{ color: "{color_a}", width: {line_width} }},
                label: {{ show: false }}
              }});
            }}
            if (cursorB !== null) {{
              lineData.push({{
                xAxis: cursorB.x,
                lineStyle: {{ color: "{color_b}", width: {line_width} }},
                label: {{ show: false }}
              }});
            }}
            var seriesUpdates = seriesList.map(function () {{
              return {{
                markLine: {{
                  symbol: ["none", "none"],
                  silent: true,
                  data: lineData
                }}
              }};
            }});
            chart.setOption({{ series: seriesUpdates }});
          }}

          function updateTable() {{
            var aLabel = document.getElementById("cursor-a-{chart_id}");
            var bLabel = document.getElementById("cursor-b-{chart_id}");
            var dLabel = document.getElementById("cursor-delta-{chart_id}");
            if (aLabel) {{
              aLabel.textContent = cursorA !== null ? cursorA.x.toFixed({time_decimals}) : "--";
            }}
            if (bLabel) {{
              bLabel.textContent = cursorB !== null ? cursorB.x.toFixed({time_decimals}) : "--";
            }}
            if (dLabel) {{
              if (cursorA !== null && cursorB !== null) {{
                dLabel.textContent = (cursorB.x - cursorA.x).toFixed({time_decimals});
              }} else {{
                dLabel.textContent = "--";
              }}
            }}

            var body = document.getElementById("cursor-body-{chart_id}");
            if (!body) {{
              return;
            }}
            var rows = body.querySelectorAll("tr");
            rows.forEach(function (row) {{
              var idx = parseInt(row.getAttribute("data-series-index"), 10);
              var series = seriesList[idx];
              var valA = cursorA !== null ? getSeriesValue(series, cursorA.idx) : null;
              var valB = cursorB !== null ? getSeriesValue(series, cursorB.idx) : null;
              var diff = null;
              if (valA !== null && valB !== null && typeof valA === "number" && typeof valB === "number") {{
                diff = valB - valA;
              }}
              var cellA = row.querySelector(".cursor-val-a");
              var cellB = row.querySelector(".cursor-val-b");
              var cellD = row.querySelector(".cursor-val-diff");
              if (cellA) {{
                cellA.textContent = formatValue(valA, {value_decimals});
              }}
              if (cellB) {{
                cellB.textContent = formatValue(valB, {value_decimals});
              }}
              if (cellD) {{
                cellD.textContent = formatValue(diff, {value_decimals});
              }}
            }});
          }}

          function setCursor(xValue, forceB) {{
            var idx = findNearestIndex(xList, xValue);
            if (idx === null) {{
              return;
            }}
            var snapped = xList[idx];
            if (forceB && cursorA !== null) {{
              cursorB = {{ x: snapped, idx: idx }};
            }} else if (cursorA === null) {{
              cursorA = {{ x: snapped, idx: idx }};
            }} else if (cursorB === null) {{
              cursorB = {{ x: snapped, idx: idx }};
            }} else {{
              cursorA = {{ x: snapped, idx: idx }};
              cursorB = null;
            }}
            updateTable();
            updateMarkLines();
          }}

          function pickXValueFromPixel(pixel) {{
            var grids = option.grid || [];
            if (!Array.isArray(grids)) {{
              grids = [grids];
            }}
            var xAxes = option.xAxis || [];
            if (!Array.isArray(xAxes)) {{
              xAxes = [xAxes];
            }}
            if (!grids.length) {{
              var fallback = chart.convertFromPixel({{ xAxisIndex: 0 }}, pixel);
              return Array.isArray(fallback) ? fallback[0] : fallback;
            }}
            for (var i = 0; i < grids.length; i++) {{
              if (!chart.containPixel({{ gridIndex: i }}, pixel)) {{
                continue;
              }}
              var axisIndex = 0;
              for (var j = 0; j < xAxes.length; j++) {{
                if (xAxes[j] && xAxes[j].gridIndex === i) {{
                  axisIndex = j;
                  break;
                }}
              }}
              var coord = chart.convertFromPixel({{ xAxisIndex: axisIndex }}, pixel);
              var xValue = Array.isArray(coord) ? coord[0] : coord;
              if (typeof xValue === "number" && isFinite(xValue)) {{
                return xValue;
              }}
            }}
            for (var k = 0; k < xAxes.length; k++) {{
              var coordAny = chart.convertFromPixel({{ xAxisIndex: k }}, pixel);
              var xAny = Array.isArray(coordAny) ? coordAny[0] : coordAny;
              if (typeof xAny === "number" && isFinite(xAny)) {{
                return xAny;
              }}
            }}
            return null;
          }}

          function getPixel(evt) {{
            if (!evt) {{
              return null;
            }}
            var domEvt = evt.event || evt;
            if (domEvt && typeof domEvt.clientX === "number" && typeof domEvt.clientY === "number") {{
              var rect = chartEl.getBoundingClientRect();
              return [domEvt.clientX - rect.left, domEvt.clientY - rect.top];
            }}
            var px = evt.offsetX;
            var py = evt.offsetY;
            if (px === undefined || py === undefined) {{
              px = evt.zrX;
              py = evt.zrY;
            }}
            return [px, py];
          }}

          chart.getZr().on("click", function (evt) {{
            var pixel = getPixel(evt);
            if (!pixel || pixel[0] === undefined || pixel[1] === undefined) {{
              return;
            }}
            var xValue = pickXValueFromPixel(pixel);
            if (typeof xValue !== "number" || !isFinite(xValue)) {{
              return;
            }}
            var shift = (evt.event && evt.event.shiftKey) || evt.shiftKey;
            setCursor(xValue, shift);
          }});

          chart.on("click", function (params) {{
            if (!params) {{
              return;
            }}
            var xValue = null;
            if (Array.isArray(params.value)) {{
              xValue = params.value[0];
            }} else if (typeof params.value === "number") {{
              xValue = params.value;
            }} else if (Array.isArray(params.data)) {{
              xValue = params.data[0];
            }}
            if (typeof xValue !== "number" || !isFinite(xValue)) {{
              return;
            }}
            var shift = params.event && params.event.shiftKey;
            setCursor(xValue, shift);
          }});
          chartEl.addEventListener("click", function (evt) {{
            var pixel = getPixel(evt);
            if (!pixel || pixel[0] === undefined || pixel[1] === undefined) {{
              return;
            }}
            var xValue = pickXValueFromPixel(pixel);
            if (typeof xValue !== "number" || !isFinite(xValue)) {{
              return;
            }}
            setCursor(xValue, evt.shiftKey);
          }});
        }}
        }})();
        </script>
        """

    def _render_bottom_with_cursor_panel(self, grid: Grid) -> str:
        html = grid.render_embed()
        chart_id = grid.chart_id
        panel_html = self._build_cursor_panel_html(chart_id)
        html = self._wrap_bottom_html(html, chart_id, panel_html)
        script = self._build_cursor_panel_script(chart_id)
        return self._inject_before_body_end(html, script)

    def plot_cycle(
        self,
        kpi_row,
        signals: dict,
        title: str = "Cycle KPI",
    ):
        # allow subclasses to control layout
        layout_kwargs = dict(self.get_layout_params())
        # Strip non-plotly keys for make_subplots
        margins = layout_kwargs.pop("margins", None)

        fig = make_subplots(**layout_kwargs)

        # 1) Availability + suppression reasons (mixed orientation)
        labels, values, colors = self._collect_availability_values(kpi_row)
        if labels:
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    name="Availability",
                    marker=dict(color=colors),
                    text=[f"{v:.1f}%" for v in values],
                    textposition="auto",
                ),
                row=1,
                col=2,
            )
            fig.update_yaxes(range=[0, 100], row=1, col=2, title="Percent")

        reason_keys, reason_vals = self._collect_suppression_values(kpi_row)
        if reason_keys:
            fig.add_trace(
                go.Bar(
                    x=reason_vals,
                    y=reason_keys,
                    orientation="h",
                    name="Suppression [%]",
                    marker=dict(color="#74c0fc"),
                    texttemplate="%{x:.1f}%",
                    textposition="inside",
                    insidetextanchor="middle",
                ),
                row=1,
                col=3,
            )
            fig.update_yaxes(autorange="reversed", row=1, col=3)
            fig.update_xaxes(range=[0, 100], row=1, col=3, title="Percent")

        # 2) Path colored by speed
        lon   = signals.get("lon")
        lat   = signals.get("lat")
        speed = signals.get("speed")

        if lon is not None and lat is not None:
            marker_kwargs = dict(size=5)
            if speed is not None:
                marker_kwargs.update(
                    color=speed,
                    coloraxis="coloraxis",
                )
            fig.add_trace(
                go.Scatter(
                    x=lon,
                    y=lat,
                    mode="markers",
                    name="Path",
                    marker=marker_kwargs,
                ),
                row=1,
                col=1,
            )

        # 3) Time-series signals (speed)
        time = signals.get("time")
        if time is not None and speed is not None:
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=speed,
                    mode="lines",
                    name="Speed",
                ),
                row=2,
                col=1,
            )

        # If a coloraxis was used, position its colorbar beside the path subplot
        if speed is not None and lon is not None and lat is not None:
            xaxis = getattr(fig.layout, "xaxis", None)
            yaxis = getattr(fig.layout, "yaxis", None)
            xdomain = xaxis.domain if xaxis and hasattr(xaxis, "domain") else None
            ydomain = yaxis.domain if yaxis and hasattr(yaxis, "domain") else None
            cb_x = (xdomain[1] + 0.015) if xdomain else 0.46
            if ydomain:
                cb_len = ydomain[1] - ydomain[0]
                cb_y = (ydomain[0] + ydomain[1]) / 2
            else:
                cb_len = 0.45
                cb_y = 0.75
            cmin, cmax = self.speed_color_range
            fig.update_layout(
                coloraxis=dict(
                    colorscale="Turbo",
                    cmin=cmin,
                    cmax=cmax,
                    colorbar=dict(
                        title=self.speed_colorbar_title,
                        title_side="right",
                        x=cb_x,
                        y=cb_y,
                        lenmode="fraction",
                        len=cb_len,
                    ),
                )
            )

        fig.update_layout(
            title=title,
            template="plotly_white",
            height=750,
        )
        if margins:
            fig.update_layout(margin=margins)

        safe_title = self._format_title_for_filename(title)
        out_path = os.path.join(self.out_dir, f"{safe_title}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")

    # ------------------------------------------------------------------ #
    def render_dashboards(self, kpi_table, feature_name, in_path_extracted):
        """
        Render dashboards for each row in the KPI table.

        Parameters
        ----------
        kpi_table : pd.DataFrame
            Cycle KPI table containing 'label' and 'feature' columns.
        feature_name : str
            Feature to filter num_rows by (e.g., 'AEB').
        in_path_extracted : str
            Directory where MF4 files are located.
        """
        if kpi_table is None or kpi_table.empty:
            return

        for _, row in kpi_table.iterrows():
            if str(row.get("feature", "")).strip().upper() != str(feature_name).strip().upper():
                continue

            label = str(row.get("label", "")).strip()
            if not label:
                continue

            fpath = os.path.join(in_path_extracted, label)
            if not os.path.exists(fpath):
                warnings.warn(f"⚠️ Cycle dashboard skipped — file not found: {fpath}")
                continue

            mdf = safe_load_mdf(fpath)
            if mdf is None:
                continue

            signals = self.prepare_signals(self.extract_cycle_signals(mdf))
            title = f"{str(feature_name).upper()} - {Path(label).stem}"
            try:
                self.plot_cycle(row, signals, title=title)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to render cycle dashboard for {label}: {e}")

    @staticmethod
    def _to_float_list(values):
        out = []
        for v in np.asarray(values):
            try:
                f = float(v)
            except Exception:
                out.append(None)
                continue
            out.append(f if np.isfinite(f) else None)
        return out

    @staticmethod
    def _format_series(values, round_decimals, cast):
        if values is None:
            return None
        out = []
        for v in values:
            if v is None:
                out.append(None)
                continue
            if cast == "int":
                try:
                    out.append(int(round(v)))
                except Exception:
                    out.append(None)
                continue
            if round_decimals is None:
                out.append(v)
                continue
            try:
                out.append(round(float(v), int(round_decimals)))
            except Exception:
                out.append(v)
        return out

    @staticmethod
    def _format_title_for_filename(title: str) -> str:
        return str(title).replace(" - ", "-").replace(" ", "_")

    @staticmethod
    def _downsample_indices(length, max_points):
        if max_points is None or max_points <= 0 or length <= max_points:
            return None
        step = int(np.ceil(length / float(max_points)))
        indices = list(range(0, length, step))
        if indices and indices[-1] != (length - 1):
            indices.append(length - 1)
        return indices

    @staticmethod
    def _apply_indices(values, indices):
        if values is None:
            return None
        if not indices:
            return list(values)
        return [values[i] for i in indices if i < len(values)]

    @staticmethod
    def _align_series_length(values, target_len):
        if target_len <= 0:
            return []
        if values is None:
            return [None] * target_len
        vals = list(values)
        if len(vals) >= target_len:
            return vals[:target_len]
        pad_value = None
        for v in reversed(vals):
            if v is not None:
                pad_value = v
                break
        return vals + [pad_value] * (target_len - len(vals))

    @staticmethod
    def _parse_series_def(series):
        key, color, label = series[:3]
        opts = {}
        if len(series) > 3:
            if isinstance(series[3], dict):
                opts.update(series[3])
        if len(series) > 4 and isinstance(series[4], dict):
            opts.update(series[4])
        opts.pop("candidates", None)
        return key, color, label, opts
