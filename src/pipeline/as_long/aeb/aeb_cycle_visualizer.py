import os

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

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
            "column_widths": [0.45, 0.25, 0.30],
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
        self.fig_top_titles = [
            "Path (colored by speed)",
            "AEB Availability",
            "AEB Suppression Breakdown",
        ]
        self.availability_defs = [
            ("Precond", "AvailDistPct", "#4c6ef5"),
            ("ROV", "aebROVAvail", "#40c057"),
            ("VAL", "aebVALAvail", "#fab005"),
        ]
        self.suppression_patterns = [
            "SteeringWheelAngleRate",
            "SteeringWheelAngle",
            "PedalPosProSuppression",
            "LatAccel",
            "YawRate",
            "LowSpeed",
        ]
        self.state_colors = {
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_UNSPECIFIED": "#adb5bd",
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_READY": "#51cf66",
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_ACTIVE": "#ff6b6b",
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_HOLD": "#ffd43b",
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_UNAVAILABLE": "#868e96",
            "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_DEGRADED": "#ffa94d",
        }
        self.default_state_color = "#adb5bd"
        self.state_defs = [
            {
                "signal_name": "aebFullState",
                "label_prefix": "aeb-fb",
                "offset_scale": 0.008,
            },
            {
                "signal_name": "aebPartialState",
                "label_prefix": "aeb-pb",
                "offset_scale": 0.014,
            },
        ]
        self.html_gap_px = 5   # vertical gap between top and bottom figures
        self.interval_pad_before_sec = 0.2
        self.interval_pad_after_sec = 0.2
        self.interval_gap_merge_sec = 2.0
        enum_file = get_resource("config/enum_definitions.yaml")
        self.enum_mapper = EnumMapper(enum_file)

    def _map_obstacle_class(self, values):
        """Map numeric obstacle class codes to names using enum definitions."""
        return self.enum_mapper.decode_values(
            "aebTargetType",
            values,
            fallback_enum="ObstacleClass",
        )

    def _decode_state_names(self, signal_name, values):
        return self.enum_mapper.decode_values(signal_name, values)

    def _build_fig_bottom(self, signals, intervals):
        time_arr = signals.get("time")
        num_intervals = len(intervals)

        if num_intervals == 0:
            fig_bottom = go.Figure()
            fig_bottom.add_annotation(
                text="No AEB intervals detected",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font_size=20,
            )
            fig_bottom.update_layout(height=600, margin=dict(l=40, r=40, t=40, b=40))
            return fig_bottom

        # === 1. Compute column widths FIRST ===
        if num_intervals > 1:
            base = [1.4] + [1.0] * (num_intervals - 1)
            total = sum(base)
            col_widths = [x / total for x in base]
        else:
            col_widths = [1.0]

        # === 2. Create fig_bottom ONCE with correct column_widths ===
        lb = self.layout_bottom

        fig_bottom = make_subplots(
            rows=lb["rows"],  # now driven by layout_bottom
            cols=num_intervals,  # dynamic
            shared_xaxes=lb["shared_xaxes"],
            vertical_spacing=lb["vertical_spacing"],
            horizontal_spacing=lb["horizontal_spacing"],
            column_widths=col_widths,
            subplot_titles=[
                f"Int {i+1}<br>{s:.1f}-{e:.1f}s" for i, (s, e) in enumerate(intervals)
            ],
        )

        # Style subplot titles: smaller font + light gray
        for ann in fig_bottom.layout.annotations:
            if "<br>" in ann.text:  # ensure we only modify interval titles
                ann.font.size = 12
                ann.font.color = "gray"
                ann.yshift = 4  # move titles closer to (-) or farther from (+) plots

        fig_bottom.update_layout(margin=lb["margins"])

        # === 3. Add all traces ===
        styles = [
            ("obstConf", "#a64ac9", "ObstConf"),
            ("posConf", "#e98b2a", "PosConf"),
            ("velConf", "#1ca9c9", "VelConf"),
            ("aebTargetType", "#c05a5a", "AEB Target Type"),
            ("longGap", "#7bb661", "LongGap"),
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
                    fig_bottom.add_trace(
                        go.Scatter(
                            x=t_seg,
                            y=y_seg,
                            mode="lines",
                            line_color=color,
                            text=texts,
                            hovertemplate="t=%{x:.2f}s<br>%{text}<extra></extra>",
                        ),
                        row=row_idx,
                        col=col_idx,
                    )
                else:
                    fig_bottom.add_trace(
                        go.Scatter(
                            x=t_seg,
                            y=y_seg,
                            mode="lines",
                            line_color=color,
                            showlegend=False,
                        ),
                        row=row_idx,
                        col=col_idx,
                    )

        # 4. === Axis formatting after all traces are added ===
        # Set x-ranges for every interval column
        for i, (start, end) in enumerate(intervals, 1):
            for row in range(1, 6):
                fig_bottom.update_xaxes(range=[start, end], row=row, col=i)

        # Row 1–3: fixed range + dtick = 0.25
        for row in [1, 2, 3]:
            for col in range(1, num_intervals + 1):
                fig_bottom.update_yaxes(range=[0, 1.1], dtick=0.25, row=row, col=col)

        # Row 4: fixed [0, 10000]
        for col in range(1, num_intervals + 1):
            fig_bottom.update_yaxes(range=[0, 10000], row=4, col=col)

        # Add row names on left-most column only
        # Use the styles list to set both title text and color
        for row_index, (_, color, label) in enumerate(styles, start=1):
            fig_bottom.update_yaxes(
                title_text=label,
                title_standoff=10,
                title_font=dict(color=color, size=13),
                row=row_index,
                col=1,
            )

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

        # Final layout
        fig_bottom.update_layout(
            height=620,
            template="plotly_white",
            showlegend=False,
            margin=dict(l=90, r=30, t=60, b=50),
        )

        return fig_bottom

    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI", extra_traces=None):
        if extra_traces is None:
            extra_traces = []

        time_arr = signals.get("time")
        long_gap = signals.get("longGap")
        intervals = self._compute_intervals(time_arr, long_gap)
        if not intervals and time_arr is not None:
            intervals = [(time_arr.min(), time_arr.max())]

        fig_top = self._build_fig_top(kpi_row, signals)
        fig_bottom = self._build_fig_bottom(signals, intervals)

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

