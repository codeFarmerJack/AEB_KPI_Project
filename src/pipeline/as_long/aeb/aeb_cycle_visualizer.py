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

    def _build_fig_bottom(self, signals):
        time_arr = signals.get("time")

        fig_bottom = make_subplots(
            rows=5,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
        )

        styles = [
            ("obstConf", "#a64ac9", "ObstConf"),
            ("posConf", "#e98b2a", "PosConf"),
            ("velConf", "#1ca9c9", "VelConf"),
            ("aebTargetType", "#c05a5a", "AEB Target Type"),
            ("longGap", "#7bb661", "LongGap"),
        ]

        for row_idx, (key, color, label) in enumerate(styles, start=1):
            data = signals.get(key)
            if data is None:
                continue

            y = np.asarray(data)

            if key == "aebTargetType":
                texts = self._map_obstacle_class(y)
                fig_bottom.add_trace(
                    go.Scatter(
                        x=time_arr,
                        y=y,
                        mode="lines",
                        line_color=color,
                        text=texts,
                        hovertemplate="t=%{x:.2f}s<br>%{text}<extra></extra>",
                    ),
                    row=row_idx,
                    col=1,
                )
            else:
                fig_bottom.add_trace(
                    go.Scatter(
                        x=time_arr,
                        y=y,
                        mode="lines",
                        line_color=color,
                    ),
                    row=row_idx,
                    col=1,
                )

            # Y-axis formatting per row
            if row_idx in (1, 2, 3):
                fig_bottom.update_yaxes(range=[0, 1.1], dtick=0.25, row=row_idx, col=1)
            elif row_idx == 4:
                fig_bottom.update_yaxes(range=[0, 10000], row=row_idx, col=1)

            fig_bottom.update_yaxes(
                title_text=label,
                title_font=dict(color=color, size=13),
                title_standoff=10,
                row=row_idx,
                col=1,
            )

        # X-axis only visible on bottom row
        for r in range(1, 5):
            fig_bottom.update_xaxes(showticklabels=False, row=r, col=1)

        fig_bottom.update_xaxes(title_text="Time [s]", row=5, col=1)

        fig_bottom.update_layout(
            height=620,
            template="plotly_white",
            showlegend=False,
            margin=dict(l=90, r=30, t=40, b=50),
        )

        return fig_bottom


    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI", extra_traces=None):
        if extra_traces is None:
            extra_traces = []

        fig_top = self._build_fig_top(kpi_row, signals)
        fig_bottom = self._build_fig_bottom(signals)

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

