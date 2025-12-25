import os
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

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        # default mapping of logical signal names to candidate mdf channels
        self.signal_candidates = self._build_signal_candidates_from_rows()
        # interval handling defaults (can be overridden in subclasses)
        self.interval_pad_before_sec = 1.0
        self.interval_pad_after_sec = 0.5
        self.interval_gap_merge_sec = 2.0
        # default layout params 
        self.layout_params = {
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
        self.bottom_row_height_px = 70
        self.bottom_row_gap_px = 16
        self.bottom_min_height_px = 650
        self.bottom_legend_pad_px = 12
        self.bottom_legend_item_gap = 0
        self.bottom_legend_gutter_px = 120
        self.bottom_legend_left_pct = 88
        self.bottom_slider_height_px = 16
        self.bottom_slider_label_gap_px = 10
        self.bottom_slider_margin_px = 6

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

    def _compute_intervals(self, time_arr, target_arr):
        """Return list of (start,end) intervals where target_arr is non-zero, merging short gaps."""
        if time_arr is None or target_arr is None:
            return []
        t = np.asarray(time_arr, dtype=float)
        tid = np.nan_to_num(np.asarray(target_arr, dtype=float), nan=0.0)
        if len(t) == 0:
            return []
        nonzero = tid != 0
        merged = nonzero.copy()
        i = 0
        while i < len(t):
            if not merged[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(t) and merged[j + 1]:
                j += 1
            k = j + 1
            while k < len(t) and not merged[k]:
                k += 1
            if k < len(t):
                gap = t[k] - t[j]
                if gap < self.interval_gap_merge_sec:
                    merged[j + 1 : k] = True
                    i = k
                    continue
            i = j + 1
        starts = np.where(merged & ~np.roll(merged, 1))[0]
        ends = np.where(merged & ~np.roll(merged, -1))[0]
        intervals = []
        for s, e in zip(starts, ends):
            intervals.append(
                (
                    t[s] - self.interval_pad_before_sec,
                    t[e] + self.interval_pad_after_sec,
                )
            )
        return intervals

    def _compute_offset_path(self, lon, lat, offset_scale=0.02, min_offset=1e-6):
        def _smooth_series(values, window=5):
            if window < 2 or len(values) < window:
                return values
            kernel = np.ones(window, dtype=float) / float(window)
            return np.convolve(values, kernel, mode="same")

        def _fill_vector_gaps(dx, dy, eps=1e-9):
            mag = np.hypot(dx, dy)
            valid = mag > eps
            if valid.all():
                return dx, dy
            idx = np.arange(len(dx))
            if valid.any():
                last = idx[valid][0]
                for i in range(last + 1, len(dx)):
                    if valid[i]:
                        last = i
                    else:
                        dx[i] = dx[last]
                        dy[i] = dy[last]
                first = idx[valid][0]
                for i in range(first - 1, -1, -1):
                    dx[i] = dx[first]
                    dy[i] = dy[first]
            else:
                dx[:] = 1.0
                dy[:] = 0.0
            return dx, dy

        lon_arr = np.asarray(lon, dtype=float)
        lat_arr = np.asarray(lat, dtype=float)
        if lon_arr.size == 0 or lat_arr.size == 0:
            return None
        mask = np.isfinite(lon_arr) & np.isfinite(lat_arr)
        if not mask.any():
            return None
        finite_lon = lon_arr[mask]
        finite_lat = lat_arr[mask]
        idx = np.arange(lon_arr.size)
        lon_filled = lon_arr.copy()
        lat_filled = lat_arr.copy()
        if not np.isfinite(lon_filled).all():
            lon_filled[~np.isfinite(lon_filled)] = np.interp(
                idx[~np.isfinite(lon_filled)],
                idx[np.isfinite(lon_filled)],
                lon_filled[np.isfinite(lon_filled)],
            )
        if not np.isfinite(lat_filled).all():
            lat_filled[~np.isfinite(lat_filled)] = np.interp(
                idx[~np.isfinite(lat_filled)],
                idx[np.isfinite(lat_filled)],
                lat_filled[np.isfinite(lat_filled)],
            )
        span = max(finite_lon.max() - finite_lon.min(), finite_lat.max() - finite_lat.min())
        if not np.isfinite(span) or span == 0:
            span = 1.0
        offset = max(span * offset_scale, min_offset)

        cx = finite_lon.mean()
        cy = finite_lat.mean()
        lon_smooth = _smooth_series(lon_filled, window=7)
        lat_smooth = _smooth_series(lat_filled, window=7)
        dx = np.gradient(lon_smooth)
        dy = np.gradient(lat_smooth)
        dx, dy = _fill_vector_gaps(dx, dy)
        mag = np.hypot(dx, dy)
        mag[mag == 0] = 1.0
        nx = -dy / mag
        ny = dx / mag
        for i in range(1, len(nx)):
            if nx[i] * nx[i - 1] + ny[i] * ny[i - 1] < 0:
                nx[i] = -nx[i]
                ny[i] = -ny[i]
        vx = lon_filled - cx
        vy = lat_filled - cy
        if np.nanmean(nx * vx + ny * vy) < 0:
            nx = -nx
            ny = -ny
        return lon_filled + nx * offset, lat_filled + ny * offset

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
                            color_map, default_color, seen_legend=None):
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
                signal_key = series[0]
                candidates_override = series[3] if len(series) > 3 else None
                # default: 1-to-1 mapping
                if candidates_override:
                    if isinstance(candidates_override, (list, tuple)):
                        candidates.setdefault(signal_key, list(candidates_override))
                    else:
                        candidates.setdefault(signal_key, [candidates_override])
                else:
                    candidates.setdefault(signal_key, [signal_key])

        return candidates

    def _add_offset_path(self, fig, lon_to_plot, lat_to_plot, signal_name, state_values,
                         label_prefix, offset_scale, state_colors, default_state_color,
                         seen_legend):
        if state_values is None:
            return

        offset_path = self._compute_offset_path(
            lon_to_plot,
            lat_to_plot,
            offset_scale=offset_scale,
        )
        if not offset_path:
            return
        lon_state, lat_state = offset_path
        state_names = self._decode_state_names(signal_name, state_values)
        self._add_state_segments(
            fig,
            lon_state,
            lat_state,
            state_names,
            label_prefix,
            row=1,
            col=1,
            color_map=state_colors,
            default_color=default_state_color,
            seen_legend=seen_legend,
        )

    def _build_fig_top(self, kpi_row, signals):
        lt = getattr(
            self,
            "layout_top",
            {
                "rows": 1,
                "cols": 3,
                "column_widths": [0.45, 0.25, 0.30],
                "horizontal_spacing": 0.10,
                "vertical_spacing": 0.00,
                "margins": {"l": 20, "r": 20, "t": 2, "b": 8},
            },
        )
        subplot_titles = getattr(
            self,
            "fig_top_titles",
            [
                "Path (colored by speed)",
                "Availability",
                "Suppression Breakdown",
            ],
        )

        fig_top = make_subplots(
            rows=lt["rows"],
            cols=lt["cols"],
            subplot_titles=subplot_titles,
            horizontal_spacing=lt["horizontal_spacing"],
            vertical_spacing=lt["vertical_spacing"],
            column_widths=lt["column_widths"],
        )

        fig_top.update_layout(margin=lt["margins"])

        # Subplot(1, 1) - Path
        lon = signals.get("lon")
        lat = signals.get("lat")
        spd = signals.get("speed")
        if lon is not None and lat is not None and spd is not None:
            # Convert to numpy arrays for easier processing
            lon_arr = np.asarray(lon, dtype=float)
            lat_arr = np.asarray(lat, dtype=float)
            spd_arr = np.asarray(spd, dtype=float)

            # === OPTIONAL: Apply Gaussian smoothing to reduce GPS noise and make path smoother ===
            # Only apply if we have enough points and valid data
            if len(lon_arr) > 10 and np.isfinite(lon_arr).any() and np.isfinite(lat_arr).any():
                from scipy.ndimage import gaussian_filter1d

                # Sigma controls smoothness: 1.0 = light, 2.0 = moderate, 3.0+ = heavy
                sigma = 1.5  # Good balance for typical driving paths

                lon_smooth = gaussian_filter1d(lon_arr, sigma=sigma)
                lat_smooth = gaussian_filter1d(lat_arr, sigma=sigma)

                # Use smoothed coordinates for the main path
                lon_to_plot = lon_smooth
                lat_to_plot = lat_smooth
            else:
                lon_to_plot = lon_arr
                lat_to_plot = lat_arr
                spd_arr = spd_arr  # fallback

            fig_top.add_trace(
                go.Scatter(
                    x=lon_to_plot,
                    y=lat_to_plot,
                    mode="lines+markers",
                    marker=dict(size=3, color=spd_arr, coloraxis="coloraxis"),
                    line=dict(width=3, color="rgba(0,0,0,0.1)"),
                    connectgaps=True,
                    showlegend=False,
                ),
                row=1,
                col=1,
            )

            state_colors = getattr(self, "state_colors", {})
            default_state_color = getattr(self, "default_state_color", "#adb5bd")
            seen_legend = set()
            state_defs = getattr(self, "state_defs", [])
            for state_def in state_defs:
                signal_name = state_def.get("signal_name")
                if not signal_name:
                    continue
                state_values = signals.get(signal_name)
                if state_values is None:
                    continue
                label_prefix = state_def.get("label_prefix", signal_name)
                offset_scale = state_def.get("offset_scale", 0.01)
                self._add_offset_path(
                    fig_top,
                    lon_to_plot,
                    lat_to_plot,
                    signal_name,
                    state_values,
                    label_prefix,
                    offset_scale,
                    state_colors,
                    default_state_color,
                    seen_legend,
                )

        fig_top.update_yaxes(scaleanchor="x", row=1, col=1)

        # Subplot(1, 2) - Availability (Feature / ROV / VAL)
        availability_defs = getattr(
            self,
            "availability_defs",
            [
                ("Availability", "AvailDistPct", "#4c6ef5"),
            ],
        )
        labels = []
        values = []
        colors = []
        for label, key, color in availability_defs:
            val = kpi_row.get(key)
            if val is None:
                continue
            labels.append(label)
            values.append(val)
            colors.append(color)

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
                row=1,
                col=2,
            )
            fig_top.update_yaxes(range=[0, 100], title_text="Percent [%]", title_standoff=5, row=1, col=2)

        # Subplot(1, 3) - Suppression breakdown
        patterns = getattr(self, "suppression_patterns", [])

        # Exact match only — no regex, no partial match
        reason_keys = [p for p in patterns if p in kpi_row]

        # retrieve values
        values = [kpi_row.get(k, 0) for k in reason_keys]

        # auto-generate display names
        labels = [k for k in reason_keys]

        # ---- Plot ----
        fig_top.add_trace(
            go.Bar(
                x=values,
                y=labels,
                orientation="h",
                marker_color="#74c0fc",
                text=[f"{v:.1f}%" for v in values],
                textposition="inside",
                showlegend=False,
            ),
            row=1,
            col=3,
        )

        fig_top.update_yaxes(autorange="reversed", row=1, col=3)
        fig_top.update_xaxes(range=[0, 100], title_text="Percent [%]", title_standoff=5, row=1, col=3)

        # Update the layout with colorbar for speed
        # Get the domain of the Path subplot (row1, col1)
        path_xaxis = fig_top.layout["xaxis"]  # xaxis = row1,col1
        path_yaxis = fig_top.layout["yaxis"]  # yaxis = row1,col1

        x0, x1 = path_xaxis.domain  # e.g., [0.0, 0.45]
        y0, y1 = path_yaxis.domain  # e.g., [0.15, 0.85]

        # Compute colorbar placement
        colorbar_x = x1  # small gap to the right of path plot
        colorbar_len = 1.1 * (y1 - y0)  # 1.1 times vertical height of subplot
        colorbar_y = (y0 + y1) / 2  # center vertically

        fig_top.update_layout(
            height=400,
            margin=dict(l=40, r=40, t=60, b=20),
            template="plotly_white",
            showlegend=True,
            barmode="group",
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.0,
                font=dict(size=10),
            ),
            coloraxis=dict(
                colorscale="Turbo",
                cmin=0,
                cmax=120,
                colorbar=dict(
                    title=dict(text="Speed [kph]", side="right"),
                    x=colorbar_x,
                    y=colorbar_y,
                    len=colorbar_len,
                    lenmode="fraction",
                    thickness=20,
                    outlinewidth=0,
                ),
            ),
        )

        return fig_top

    def _build_fig_bottom(self, signals: dict):
        if not self.row_defs:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define row_defs"
            )

        time_arr = signals.get("time")
        if time_arr is None:
            raise ValueError("Missing 'time' signal")

        # === build active_rows from self.row_defs ===
        active_rows = []
        for row in self.row_defs:
            series_data = []
            for series in row["series"]:
                key, color, label = series[:3]
                data = signals.get(key)
                if data is None:
                    continue
                series_data.append(
                    {
                        "label": label,
                        "color": color,
                        "y": self._to_float_list(data),
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
        legend_pad_px = self.bottom_legend_pad_px
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

        x = np.asarray(time_arr, dtype=float).tolist()
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
        value_label = opts.LabelOpts(
            is_show=True,
            formatter=JsCode(
                """
                function (params) {
                    var d = params.data;
                    var v = d;
                    if (d && typeof d === 'object') {
                        if (d.name !== undefined && d.name !== null && d.name !== '') {
                            v = d.name;
                        } else if (d.value !== undefined) {
                            v = d.value;
                        }
                    }
                    if (Array.isArray(v)) {
                        v = v[v.length - 1];
                    }
                    if (typeof v === 'number') {
                        v = v.toFixed(3);
                    }
                    return v;
                }
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

            y_min, y_max = None, None
            if row.get("y_range"):
                y_min, y_max = row["y_range"]

            row_height = row["height_px"] * scale
            plot_height = max(row_height - legend_pad, 1)

            legend_orient = "vertical" if len(row["series"]) > 1 else "horizontal"
            legend_opts = opts.LegendOpts(
                is_show=True,
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

            unit = row.get("unit")
            yaxis_name = f"[{unit}]" if unit else ""
            yaxis_kwargs = {
                "name": yaxis_name,
                "name_location": "middle",
                "name_rotate": 90,
                "name_gap": 20,
                "axispointer_opts": opts.AxisPointerOpts(
                    is_show=False,
                    label=opts.LabelOpts(is_show=False),
                ),
                "split_number": 4,
            }

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
                    pos_right=f"{self.bottom_legend_gutter_px}px",
                    pos_top=f"{top_pct + legend_pad}%",
                    height=f"{plot_height}%",
                ),
            )

            top_pct += row_height + row_gap

        return grid


    def plot_cycle(
        self,
        kpi_row,
        signals: dict,
        title: str = "Cycle KPI",
        extra_traces: list | None = None,
    ):
        # allow subclasses to control layout and signals
        layout_kwargs = dict(self.get_layout_params())
        # Strip non-plotly keys for make_subplots
        margins = layout_kwargs.pop("margins", None)
        signals = self.prepare_signals(signals)

        fig = make_subplots(**layout_kwargs)

        # 1) Availability + suppression reasons (mixed orientation)
        overall = kpi_row.get("AvailDistPct")
        reason_keys = [
            k
            for k in [
                "PedalPosProSuppression",
                "SteeringWheelAngle",
                "SteeringWheelAngleRate",
                "YawRate",
                "LatAccel",
                "LowSpeed",
            ]
            if k in kpi_row
        ]

        if overall is not None:
            fig.add_trace(
                go.Bar(
                    x=["AvailDistPct"],
                    y=[overall],
                    name="Availability",
                    marker=dict(color="#4c6ef5"),
                    texttemplate="%{y:.1f}%",
                    textposition="auto",
                ),
                row=1,
                col=2,
            )
            fig.update_yaxes(range=[0, 100], row=1, col=2, title="Percent")

        if reason_keys:
            reason_labels = list(reason_keys)
            reason_vals = [kpi_row.get(k, 0) for k in reason_keys]
            fig.add_trace(
                go.Bar(
                    x=reason_vals,
                    y=reason_labels,
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

        # 4) Optional extra traces on the signals row
        if extra_traces:
            for tr in extra_traces:
                fig.add_trace(tr, row=2, col=1)

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
            fig.update_layout(
                coloraxis=dict(
                    colorscale="Turbo",
                    cmin=0,
                    cmax=120,
                    colorbar=dict(
                        title="Speed [kph]",
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

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
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

            signals = self.extract_cycle_signals(mdf)
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
