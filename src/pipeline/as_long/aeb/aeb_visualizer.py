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
            "horizontal_spacing": 0.13,
            "vertical_spacing": 0.00,
            "margins": {"l": 0, "r": 0, "t": 10, "b": 8},
        }
        # Bottom interval grid (5 stacked rows × N intervals)
        self.layout_bottom = {
            "rows": 5,                    
            "shared_xaxes": True,
            "vertical_spacing": 0.04,
            "horizontal_spacing": 0.02,
            # column_widths is dynamic (depends on num_intervals)
            "margins": {"l": 0, "r": 0, "t": 50, "b": 8},
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


        # Path
        lon = signals.get("lon")
        lat = signals.get("lat")
        spd = signals.get("speed")
        if lon is not None and lat is not None and spd is not None:
            fig_top.add_trace(go.Scatter(
                x=lon, y=lat,
                mode="lines+markers",
                marker=dict(size=5, color=spd, coloraxis="coloraxis"),
                line=dict(width=0.5, color="rgba(0,0,0,0.1)"),
                showlegend=False
            ), row=1, col=1)

        fig_top.update_yaxes(scaleanchor="x", row=1, col=1)

        # Availability
        avail = kpi_row.get("AvailDistPct")
        if avail is not None:
            fig_top.add_trace(go.Bar(
                x=[""], y=[avail],
                marker_color="#4c6ef5",
                text=f"{avail:.1f}%",
                textposition="inside"
            ), row=1, col=2)
            fig_top.update_yaxes(range=[0, 100], title_text="Percent", row=1, col=2)

        # ----------------------------------------------
        # Wild search for suppression-related KPI values
        # ----------------------------------------------

        # patterns to search for
        patterns = [
            r"SteeringWheelAngleRate",
            r"SteeringWheelAngle",
            r"PedalPosProSuppression",         
            r"LatAccel",
            r"YawRate",
            r"LowSpeed",
        ]

        # find matching keys in kpi_row
        reason_keys = [
            k for k in kpi_row.keys()
            if any(re.search(p, k, re.IGNORECASE) for p in patterns)
        ]

        # preserve deterministic order
        reason_keys.sort()

        # retrieve values
        values = [kpi_row.get(k, 0) for k in reason_keys]

        # auto-generate display names
        labels = [f"{k} [%]" for k in reason_keys]

        # ---- Plot ----
        fig_top.add_trace(
            go.Bar(
                x=values, y=labels, orientation="h",
                marker_color="#74c0fc",
                text=[f"{v:.1f}%" for v in values],
                textposition="inside",
            ),
            row=1, col=3
        )

        fig_top.update_yaxes(autorange="reversed", row=1, col=3)
        fig_top.update_xaxes(range=[0, 100], title_text="Percent", row=1, col=3)

        # Get the domain of the Path subplot (row1, col1)
        path_xaxis = fig_top.layout["xaxis"]       # xaxis = row1,col1
        path_yaxis = fig_top.layout["yaxis"]       # yaxis = row1,col1

        x0, x1 = path_xaxis.domain                 # e.g., [0.0, 0.45]
        y0, y1 = path_yaxis.domain                 # e.g., [0.15, 0.85]

        # Compute colorbar placement
        colorbar_x = x1                  # small gap to the right of path plot
        colorbar_len = y1 - y0           # exact vertical height of subplot
        colorbar_y = (y0 + y1) / 2       # center vertically


        fig_top.update_layout(
            height=400,
            margin=dict(l=40, r=40, t=60, b=20),
            template="plotly_white",
            showlegend=False,
            coloraxis=dict(
                colorscale="Turbo",
                cmin=0,
                cmax=120,
                colorbar=dict(
                    title="Speed [kph]",
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
        # BOTTOM FIGURE: Dynamic intervals (CORRECT ORDER!)
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

            fig_bottom.update_layout(margin=lb["margins"])


            # === 3. NOW add all traces (this was already correct) ===
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
