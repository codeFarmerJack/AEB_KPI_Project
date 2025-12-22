import os
import re
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from src.viz.visualizers.base_event_visualizer import BaseEventVisualizer
from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer
from src.utils.enum_loader import EnumMapper
from src.utils.path_manager import get_resource


class AebCycleVisualizer(BaseCycleVisualizer):
    """
    Feature-specific cycle visualizer for AEB.
    """
    def __init__(self, out_dir: str):
        # Initialize with feature-specific signal candidates
        super().__init__(out_dir)
        self.signal_candidates = {
            "time": ["time"],
            "lon": ["longitude"],
            "lat": ["latitude"],
            "speed": ["egoSpeedKph"],
            "aebFullState": ["aebFullState"],
            "aebPartialState": ["aebPartialState"],
            "obstConf": ["obstConf"],
            "posConf": ["posConf"],
            "velConf": ["velConf"],
            "aebTargetType": ["aebTargetType"],
            "longGap": ["longGap"],
        }
        self.layout_top = {
            "rows": 1,
            "cols": 3,
            "column_widths": [0.45, 0.15, 0.40],
            "horizontal_spacing": 0.10,
            "vertical_spacing": 0.00,
            "margins": {"l": 20, "r": 20, "t": 2, "b": 8},
        }
        # Bottom interval grid (5 stacked rows × N intervals)
        self.layout_bottom = {
            "rows": 5,                    
            "shared_xaxes": True,
            "vertical_spacing": 0.04,
            "horizontal_spacing": 0.02,
            # column_widths is dynamic (depends on num_intervals)
            "margins": {"l": 0, "r": 0, "t": 10, "b": 8},
        }
        self.html_gap_px = 5   # vertical gap between top and bottom figures
        self.interval_pad_before_sec = 0.2
        self.interval_pad_after_sec = 0.2
        self.interval_gap_merge_sec = 2.0
        enum_file = get_resource("config/enum_definitions.yaml")
        self.enum_mapper = EnumMapper(enum_file)

    def extract_cycle_signals(self, mdf):
        """
        Feature-specific signal selection for AEB cycle dashboards.
        """
        return super().extract_cycle_signals(mdf)

    def _map_obstacle_class(self, values):
        """Map numeric obstacle class codes to names using enum definitions."""
        if values is None:
            return None
        mapped = []
        for v in np.asarray(values):
            try:
                code = int(v)
            except Exception:
                mapped.append(None)
                continue
            enum_name = self.enum_mapper.get_enum_for_value("aebTargetType") or "ObstacleClass"
            mapped.append(self.enum_mapper.to_name(enum_name, code) or code)
        return mapped

    def _decode_state_names(self, signal_name, values):
        if values is None:
            return None
        enum_name = (
            self.enum_mapper.get_enum_for_value(signal_name)
            or self.enum_mapper.get_enum_for_signal(signal_name)
        )
        names = []
        for v in np.asarray(values):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                names.append(None)
                continue
            if isinstance(v, str):
                names.append(v)
                continue
            try:
                code = int(v)
            except Exception:
                names.append(None)
                continue
            if enum_name:
                names.append(self.enum_mapper.to_name(enum_name, code) or str(code))
            else:
                names.append(str(code))
        return names

    def _compute_offset_path(self, lon, lat, offset_scale=0.02, min_offset=1e-6, ):
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

    def _add_state_segments(self, fig, x, y, state_names, label_prefix, row, col, color_map, default_color, seen_legend=None,):
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

    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI", extra_traces=None):
        if extra_traces is None:
            extra_traces = []

        time_arr = signals.get("time")
        long_gap = signals.get("longGap")
        intervals = self._compute_intervals(time_arr, long_gap)
        if not intervals and time_arr is not None:
            intervals = [(time_arr.min(), time_arr.max())]

        num_intervals = len(intervals)

        # ================================
        # TOP FIGURE: 3 fixed plots
        # ================================
        lt = self.layout_top

        fig_top = make_subplots(
            rows=lt["rows"],
            cols=lt["cols"],
            subplot_titles=[
                "Path (colored by speed)",
                "AEB Availability",
                "AEB Suppression Breakdown",
            ],
            horizontal_spacing=lt["horizontal_spacing"],
            vertical_spacing=lt["vertical_spacing"],
            column_widths=lt["column_widths"],
        )

        fig_top.update_layout(margin=lt["margins"])


        # Subplot(1, 1) - Path
        lon = signals.get("lon")
        lat = signals.get("lat")
        spd = signals.get("speed")
        aeb_full_state = signals.get("aebFullState")
        aeb_partial_state = signals.get("aebPartialState")
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
                
            fig_top.add_trace(go.Scatter(
                x=lon_to_plot, y=lat_to_plot,
                mode="lines+markers",
                marker=dict(size=3, color=spd_arr, coloraxis="coloraxis"),
                line=dict(width=3, color="rgba(0,0,0,0.1)"),
                connectgaps=True,
                showlegend=False
            ), row=1, col=1)

            state_colors = {
                "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_UNSPECIFIED": "#adb5bd",
                "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_READY": "#51cf66",
                "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_ACTIVE": "#ff6b6b",
                "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_HOLD": "#ffd43b",
                "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_UNAVAILABLE": "#868e96",
                "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_DEGRADED": "#ffa94d",
            }
            default_state_color = "#adb5bd"
            seen_legend = set()
            offset_path = self._compute_offset_path(lon_to_plot, lat_to_plot, offset_scale=0.008)
            if offset_path and aeb_full_state is not None:
                lon_full, lat_full = offset_path
                full_names = self._decode_state_names("aebFullState", aeb_full_state)
                self._add_state_segments(
                    fig_top,
                    lon_full,
                    lat_full,
                    full_names,
                    "aeb-fb",
                    row=1,
                    col=1,
                    color_map=state_colors,
                    default_color=default_state_color,
                    seen_legend=seen_legend,
                )
            offset_path = self._compute_offset_path(lon_to_plot, lat_to_plot, offset_scale=0.014)
            if offset_path and aeb_partial_state is not None:
                lon_partial, lat_partial = offset_path
                partial_names = self._decode_state_names("aebPartialState", aeb_partial_state)
                self._add_state_segments(
                    fig_top,
                    lon_partial,
                    lat_partial,
                    partial_names,
                    "aeb-pb",
                    row=1,
                    col=1,
                    color_map=state_colors,
                    default_color=default_state_color,
                    seen_legend=seen_legend,
                )

        fig_top.update_yaxes(scaleanchor="x", row=1, col=1)

        # Subplot(1, 2) - Availability
        avail = kpi_row.get("AvailDistPct")
        if avail is not None:
            fig_top.add_trace(go.Bar(
                x=[""], y=[avail],
                marker_color="#4c6ef5",
                text=f"{avail:.1f}%",
                textposition="inside",
                showlegend=False,
            ), row=1, col=2)
            fig_top.update_yaxes(range=[0, 100], title_text="Percent [%]", title_standoff=5, row=1, col=2)

        # Subplot(1, 3) - Suppression breakdown
        
        patterns = [
            "SteeringWheelAngleRate",
            "SteeringWheelAngle",
            "PedalPosProSuppression",
            "LatAccel",
            "YawRate",
            "LowSpeed",
        ]

        # Exact match only — no regex, no partial match
        reason_keys = [p for p in patterns if p in kpi_row]


        # retrieve values
        values = [kpi_row.get(k, 0) for k in reason_keys]

        # auto-generate display names
        labels = [k for k in reason_keys]

        # ---- Plot ----
        fig_top.add_trace(
            go.Bar(
                x=values, y=labels, orientation="h",
                marker_color="#74c0fc",
                text=[f"{v:.1f}%" for v in values],
                textposition="inside",
                showlegend=False,
            ),
            row=1, col=3
        )

        fig_top.update_yaxes(autorange="reversed", row=1, col=3)
        fig_top.update_xaxes(range=[0, 100], title_text="Percent [%]", title_standoff=5, row=1, col=3)

        # Update the layout with colorbar for speed
        # Get the domain of the Path subplot (row1, col1)
        path_xaxis = fig_top.layout["xaxis"]       # xaxis = row1,col1
        path_yaxis = fig_top.layout["yaxis"]       # yaxis = row1,col1

        x0, x1 = path_xaxis.domain                 # e.g., [0.0, 0.45]
        y0, y1 = path_yaxis.domain                 # e.g., [0.15, 0.85]

        # Compute colorbar placement
        colorbar_x = x1                  # small gap to the right of path plot
        colorbar_len = 1.1 * (y1 - y0)   # 1.1 times vertical height of subplot
        colorbar_y = (y0 + y1) / 2       # center vertically

        fig_top.update_layout(
            height=400,
            margin=dict(l=40, r=40, t=60, b=20),
            template="plotly_white",
            showlegend=True,
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
                    outlinewidth=0
                )
            )
        )


        # ================================
        # BOTTOM FIGURE: Dynamic intervals
        # ================================
        if num_intervals == 0:
            fig_bottom = go.Figure()
            fig_bottom.add_annotation(
                text="No AEB intervals detected", x=0.5, y=0.5,
                xref="paper", yref="paper", showarrow=False, font_size=20
            )
            fig_bottom.update_layout(height=600, margin=dict(l=40, r=40, t=40, b=40))
        else:
            # === 1. Compute column widths FIRST ===
            if num_intervals > 1:
                base = [1.4] + [1.0] * (num_intervals - 1)
                total = sum(base)
                col_widths = [x / total for x in base]
            else:
                col_widths = [1.0]

            # === 2. Create fig_bottom ONCE with correct column_widths ===
            lb = self.layout_bottom

            # col_widths is computed from num_intervals elsewhere, e.g.
            # col_widths = [1.0 / num_intervals] * num_intervals
            fig_bottom = make_subplots(
                rows=lb["rows"],          # ← now driven by layout_bottom
                cols=num_intervals,       # dynamic
                shared_xaxes=lb["shared_xaxes"],
                vertical_spacing=lb["vertical_spacing"],
                horizontal_spacing=lb["horizontal_spacing"],
                column_widths=col_widths,
                subplot_titles=[
                    f"Int {i+1}<br>{s:.1f}-{e:.1f}s"
                    for i, (s, e) in enumerate(intervals)
                ],
            )

            # Style subplot titles: smaller font + light gray
            for ann in fig_bottom.layout.annotations:
                if "<br>" in ann.text:  # ensure we only modify interval titles
                    ann.font.size = 12
                    ann.font.color = "gray"
                    ann.yshift = 4   # move titles closer to (-) or farther from (+) plots

            fig_bottom.update_layout(margin=lb["margins"])

            # === 3. Add all traces ===
            styles = [
                ("obstConf",      "#a64ac9", "ObstConf"),
                ("posConf",       "#e98b2a", "PosConf"),
                ("velConf",       "#1ca9c9", "VelConf"),
                ("aebTargetType", "#c05a5a", "AEB Target Type"),
                ("longGap",       "#7bb661", "LongGap"),
            ]

            for col_idx, (start, end) in enumerate(intervals, 1):
                mask = (time_arr >= start) & (time_arr <= end)
                t_seg = time_arr[mask]

                # Add all 5 traces for this interval
                for row_idx, (key, color, label) in enumerate(styles, 1):
                    data = signals.get(key)
                    if data is None or len(np.asarray(data)[mask]) == 0:
                        continue
                    y_seg = np.asarray(data)[mask]

                    if key == "aebTargetType":
                        texts = self._map_obstacle_class(y_seg)
                        fig_bottom.add_trace(go.Scatter(
                            x=t_seg, y=y_seg, mode="lines", line_color=color,
                            text=texts,
                            hovertemplate="t=%{x:.2f}s<br>%{text}<extra></extra>"
                        ), row=row_idx, col=col_idx)
                    else:
                        fig_bottom.add_trace(go.Scatter(
                            x=t_seg, y=y_seg, mode="lines", line_color=color, showlegend=False
                        ), row=row_idx, col=col_idx)
            
            # 4. === Axis formatting after all traces are added ===
            if num_intervals > 0:

                # Set x-ranges for every interval column
                for i, (start, end) in enumerate(intervals, 1):
                    for row in range(1, 6):
                        fig_bottom.update_xaxes(range=[start, end], row=row, col=i)

                # -------------------------------------------
                # Row 1–3: fixed range + dtick = 0.25
                # -------------------------------------------
                for row in [1, 2, 3]:
                    for col in range(1, num_intervals + 1):
                        fig_bottom.update_yaxes(
                            range=[0, 1.1],
                            dtick=0.25,
                            row=row,
                            col=col
                        )

                # Row 4: fixed [0, 10000]
                for col in range(1, num_intervals + 1):
                    fig_bottom.update_yaxes(range=[0, 10000], row=4, col=col)

                # Row 5: adaptive (no range)

                # -------------------------------------------
                # Add row names on left-most column only
                # -------------------------------------------
                # Use the styles list to set both title text and color
                for row_index, (_, color, label) in enumerate(styles, start=1):
                    fig_bottom.update_yaxes(
                        title_text=label,
                        title_standoff=10,
                        title_font=dict(color=color, size=13),
                        row=row_index,
                        col=1
                    )

                # -------------------------------------------
                # Tick visibility rules
                # -------------------------------------------
                # Hide y-ticks on all columns except the first
                for row in range(1, 6):
                    for col in range(2, num_intervals + 1):
                        fig_bottom.update_yaxes(showticklabels=False, row=row, col=col)

                # Only bottom row shows x-axis ticks
                for col in range(1, num_intervals + 1):
                    fig_bottom.update_xaxes(showticklabels=True, row=5, col=col)

                for row in range(1, 5):
                    for col in range(1, num_intervals + 1):
                        fig_bottom.update_xaxes(showticklabels=False, row=row, col=col)

                # -------------------------------------------
                # Final layout
                # -------------------------------------------
                fig_bottom.update_layout(
                    height=620,
                    template="plotly_white",
                    showlegend=False,
                    margin=dict(l=90, r=30, t=60, b=50),
                )



        # ================================
        # COMBINE & SAVE
        # ================================
        html_top = pio.to_html(fig_top, include_plotlyjs="cdn", full_html=False)
        html_bottom = pio.to_html(fig_bottom, include_plotlyjs=False, full_html=False)

        full_html = f"""
        <html><head><title>{title}</title></head>
        <body style="margin:0; padding:20px; background:#f9f9f9;">
            <h2 style="text-align:center; color:#1e3d73;">{title}</h2>
            {html_top}
            <div style="height:{self.html_gap_px}px;"></div>
            {html_bottom}
        </body></html>
        """

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"Cycle dashboard saved → {out_path}")

class AebEventVisualizer(BaseEventVisualizer):
    """AEB KPI visualizer routed through the shared viz module."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")
