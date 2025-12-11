import os
import numpy as np
import plotly.graph_objects as go
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
            "obstConf": ["obstConf"],
            "posConf": ["posConf"],
            "velConf": ["velConf"],
            "aebTargetType": ["aebTargetType"],
            "longGap": ["longGap"],
        }
        # Feature-specific layout defaults (override base if needed)
        self.layout_params = {
            "rows": 6,
            "cols": 3,
            "shared_xaxes": False,
            "column_widths": [0.45, 0.15, 0.40],
            "row_heights": [0.32, 0.16, 0.16, 0.16, 0.1, 0.1],
            # Row-1 gap control: increase to widen spacing between top plots.
            # Suggested range: 0.0–0.2 (will be clamped to Plotly's max spacing)
            "horizontal_spacing": 0.15,
            # Rows 2–6 gap control: 0 = no gap, higher values widen body columns.
            "body_horizontal_spacing": 0.0,
            "vertical_spacing": 0.04,
            # Figure margins (adjust these to affect apparent horizontal gaps)
            "margins": {"l": 0, "r": 0, "t": 60, "b": 8},
            "width": 1800,
        }
        self.interval_pad_before_sec = 1.0
        self.interval_pad_after_sec = 0.5
        self.interval_gap_merge_sec = 2.0
        enum_file = get_resource("config/enum_definitions.yaml")
        self.enum_mapper = EnumMapper(enum_file)

    def get_layout_params(self):
        """
        Customize the layout titles to be AEB specific.
        """
        return dict(self.layout_params)

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

    def plot_cycle(
        self,
        kpi_row,
        signals: dict,
        title: str = "Cycle KPI",
        extra_traces: list | None = None,
    ):
        """
        Extend base plot with AEB-specific rows: ObstConf, PosConf, VelConf, TargetType.
        Dynamically adds one signals row per target-ID interval to avoid large blank spans.
        """
        num_rows_cfg = self.layout_params.get("rows", 6)
        min_cols_cfg = self.layout_params.get("cols", 3)

        if not isinstance(signals, dict):
            # Defensive guard: extractor must yield a dict of arrays
            return
        time_arr = signals.get("time")
        long_gap = signals.get("longGap")

        intervals = self._compute_intervals(time_arr, long_gap)
        if not intervals:
            intervals = [(time_arr.min() if time_arr is not None else 0, time_arr.max() if time_arr is not None else 1)]

        num_cols = max(min_cols_cfg, len(intervals))

        # NEW subplot grid with configurable rows and evenly spaced row 1
        NUM_ROWS = num_rows_cfg  # new row count

        # Build specs
        row1_specs = [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]
        row1_specs += [None] * max(0, num_cols - 3)
        specs = [row1_specs]

        # Next 5 signal rows
        for _ in range(NUM_ROWS - 1):
            specs.append([{"type": "xy"} for _ in range(num_cols)])

        # Column widths
        if num_cols <= 3:
            col_widths = list(self.layout_params["column_widths"])
        else:
            col_widths = [1.0 / num_cols] * num_cols

        # Titles for ONLY the first row (3 plots)
        titles = [
            "Path (colored by speed)",
            "AEB Availability",
            "AEB Suppression Breakdown"
        ]

        # Fill the rest with empty titles so Plotly doesn’t draw text
        num_other_cells = (NUM_ROWS * num_cols) - 3  
        titles += ["" for _ in range(num_other_cells)]
        
        # Compute horizontal spacing (keep your old logic)
        max_spacing = 1.0 / (num_cols - 1) if num_cols > 1 else 0
        desired_spacing = self.layout_params["horizontal_spacing"]
        # Clamp to Plotly's limit to avoid domain overflow when many columns
        horiz_spacing = min(desired_spacing, max_spacing * 0.8) if max_spacing > 0 else 0.0

        fig = make_subplots(
            rows=NUM_ROWS,
            cols=num_cols,
            specs=specs,
            subplot_titles=titles,
            vertical_spacing=self.layout_params["vertical_spacing"],
            horizontal_spacing=horiz_spacing,
            column_widths=col_widths,
            row_heights=self.layout_params["row_heights"],
        )
        fig.update_layout(showlegend=False)

        # Apply body horizontal spacing to rows 2–6
        body_gap = self.layout_params.get("body_horizontal_spacing", 0.0)
        body_gap = max(0.0, min(body_gap, 0.2))
        usable = max(1.0 - body_gap * (num_cols - 1), 0.01)
        body_width = usable / num_cols
        col_domains = []
        start = 0.0
        for _ in range(num_cols):
            end = min(1.0, start + body_width)
            col_domains.append((start, end))
            start = end + body_gap

        grid = getattr(fig, "_grid_ref", None)
        if grid:
            for r_idx, row_cells in enumerate(grid, start=1):
                for c_idx, cell in enumerate(row_cells, start=1):
                    if r_idx < 2 or c_idx > len(col_domains):
                        continue
                    xaxis_name = None
                    if isinstance(cell, dict):
                        xaxis_name = cell.get("xaxis")
                    elif isinstance(cell, (tuple, list)):
                        if cell and isinstance(cell[0], str) and cell[0].startswith("x"):
                            xaxis_name = cell[0]
                        elif len(cell) > 1 and isinstance(cell[1], (tuple, list)) and cell[1]:
                            maybe = cell[1][0]
                            if isinstance(maybe, str) and maybe.startswith("x"):
                                xaxis_name = maybe
                    if xaxis_name and xaxis_name in fig.layout:
                        fig.layout[xaxis_name].domain = list(col_domains[c_idx - 1])


        def add_availability():
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
                reason_labels = [k.replace("Suppression", "") for k in reason_keys]
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

        def add_path():
            lon = signals.get("lon")
            lat = signals.get("lat")
            spd = signals.get("speed")
            if lon is None or lat is None:
                return spd
            if spd is None:
                marker_kwargs = dict(size=5, color="#8b0000")
                fig.add_trace(
                    go.Scatter(x=lon, y=lat, mode="lines+markers", name="Path", marker=marker_kwargs),
                    row=1,
                    col=1,
                )
                return spd

            # Use line gradient via colorscale on marker positions; connect points
            fig.add_trace(
                go.Scatter(
                    x=lon,
                    y=lat,
                    mode="lines+markers",
                    name="Path",
                    line=dict(color="rgba(0,0,0,0)"),  # hide solid line, rely on marker color grad
                    marker=dict(
                        size=5,
                        color=spd,
                        colorscale="Turbo",
                        coloraxis="coloraxis",
                    ),
                ),
                row=1,
                col=1,
            )
            return spd

        add_availability()
        spd_for_colorbar = add_path()

        def slice_interval(start, end, series):
            if series is None or time_arr is None:
                return None, None
            mask = (time_arr >= start) & (time_arr <= end)
            return time_arr[mask], np.asarray(series)[mask]

        if not intervals:
            intervals = [(time_arr.min() if time_arr is not None else 0, time_arr.max() if time_arr is not None else 1)]

        row_styles = {
            2: {"color": "#a64ac9", "ylabel": "ObstConf"},
            3: {"color": "#e98b2a", "ylabel": "PosConf"},
            4: {"color": "#1ca9c9", "ylabel": "VelConf"},
            5: {"color": "#c05a5a", "ylabel": "AEB Target Type"},
            6: {"color": "#7bb661", "ylabel": "LongGap"},
        }

        for seg_idx, (start, end) in enumerate(intervals):
            col = seg_idx + 1
            t_seg, obst = slice_interval(start, end, signals.get("obstConf"))
            if t_seg is not None and obst is not None:
                fig.add_trace(
                    go.Scatter(
                        x=t_seg,
                        y=obst,
                        mode="lines",
                        name=f"ObstConf {col}",
                        line=dict(color=row_styles[2]["color"]),
                    ),
                    row=2,
                    col=col,
                )
                fig.update_xaxes(range=[start, end], row=2, col=col)
            t_seg, pos = slice_interval(start, end, signals.get("posConf"))
            if t_seg is not None and pos is not None:
                fig.add_trace(
                    go.Scatter(
                        x=t_seg,
                        y=pos,
                        mode="lines",
                        name=f"PosConf {col}",
                        line=dict(color=row_styles[3]["color"]),
                    ),
                    row=3,
                    col=col,
                )
                fig.update_xaxes(range=[start, end], row=3, col=col)
            t_seg, vel = slice_interval(start, end, signals.get("velConf"))
            if t_seg is not None and vel is not None:
                fig.add_trace(
                    go.Scatter(
                        x=t_seg,
                        y=vel,
                        mode="lines",
                        name=f"VelConf {col}",
                        line=dict(color=row_styles[4]["color"]),
                    ),
                    row=4,
                    col=col,
                )
                fig.update_xaxes(range=[start, end], row=4, col=col)
            # Row 5 → AEB Target Type
            t_seg, obst_type = slice_interval(start, end, signals.get("aebTargetType"))
            if t_seg is not None and obst_type is not None:
                labels = self._map_obstacle_class(obst_type)
                fig.add_trace(
                    go.Scatter(
                        x=t_seg,
                        y=obst_type,
                        mode="lines",
                        name=f"AEB Target Type {col}",
                        text=labels,
                        line=dict(color=row_styles[5]["color"]),
                        hovertemplate="t=%{x:.2f}s<br>code=%{y}<br>type=%{text}<extra></extra>",
                    ),
                    row=5,
                    col=col,
                )
                fig.update_xaxes(range=[start, end], row=5, col=col)

            # Row 6 → LongGap
            t_seg, tid = slice_interval(start, end, signals.get("longGap"))
            if t_seg is not None and tid is not None:
                fig.add_trace(
                    go.Scatter(
                        x=t_seg,
                        y=tid,
                        mode="lines",
                        name=f"LongGap {col}",
                        line=dict(color=row_styles[6]["color"]),
                    ),
                    row=6,
                    col=col,
                )
                fig.update_xaxes(range=[start, end], row=6, col=col)

        if extra_traces:
            for tr in extra_traces:
                fig.add_trace(tr, row=2, col=1)

        # Axis formatting per requirements
        for c in range(1, num_cols + 1):
            fig.update_yaxes(range=[0, 1], dtick=0.25, row=2, col=c, showticklabels=(c == 1))
            fig.update_yaxes(range=[0, 1], dtick=0.25, row=3, col=c, showticklabels=(c == 1))
            fig.update_yaxes(range=[0, 1], dtick=0.25, row=4, col=c, showticklabels=(c == 1))
            fig.update_yaxes(showticklabels=False, title_text=None, row=5, col=c)
            fig.update_yaxes(showticklabels=False, title_text=None, row=6, col=c)
            fig.update_xaxes(showticklabels=False, title_text=None, row=2, col=c)
            fig.update_xaxes(showticklabels=False, title_text=None, row=3, col=c)
            fig.update_xaxes(showticklabels=False, title_text=None, row=4, col=c)
            fig.update_xaxes(showticklabels=False, title_text=None, row=5, col=c)

        # Set y-axis titles on first column for each signal row
        for row_idx, meta in row_styles.items():
            fig.update_yaxes(title_text=meta["ylabel"], row=row_idx, col=1)

        if spd_for_colorbar is not None and signals.get("lon") is not None and signals.get("lat") is not None:
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

        fig.update_layout(title=title, template="plotly_white", height=1000, width=self.layout_params.get("width", None))
        # Trim outer margins to squeeze horizontal space
        fig.update_layout(margin=self.layout_params["margins"])
        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")


class AebEventVisualizer(BaseEventVisualizer):
    """AEB KPI visualizer routed through the shared viz module."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")
