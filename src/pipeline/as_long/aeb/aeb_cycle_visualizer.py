import os

import numpy as np
import plotly.io as pio

from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer
from src.utils.enum_loader import EnumMapper
from src.utils.path_manager import get_resource


class AebCycleVisualizer(BaseCycleVisualizer):
    """
    Feature-specific cycle visualizer for AEB.
    """
    row_defs = [
            {
                "label": "EgoSpeedKph",
                "height_px": 70,
                "unit": "kph",
                "series": [
                    ("egoSpeedKph", "#4c6ef5", "EgoSpeedKph"),
                ],
            },
            {
                "label": "Accel/TargetDecel",
                "height_px": 70,
                "unit": "m/s2",
                "y_range": (-12, 1),
                "series": [
                    ("longActAccel", "#2f9e44", "LongActAccel"),
                    ("aebTargetDecel", "#d9480f", "AebTargetDecel"),
                ],
            },
            {
                "label": "AEB State",
                "height_px": 40,
                "unit": None,
                "series": [
                    ("aebFullState", "#3007fe", "AebFullState"),
                    ("aebPartialState", "#ed0808", "AebPartialState"),
                ],
            },
            {
                "label": "LongGap",
                "height_px": 70,
                "unit": "m",
                "series": [
                    ("longGap", "#7bb661", "LongGap"),
                ],
            },
            {
                "label": "Throttle",
                "height_px": 70,
                "unit": "%",
                "series": [
                    ("throttleValue", "#ffa94d", "ThrottleValue"),
                ],
            },
            {
                "label": "Precond/Abort",
                "height_px": 40,
                "unit": None,
                "series": [
                    ("aebPrecondBlk", "#5c7cfa", "AebPrecondBlk"),
                    ("aebAbort", "#f03e3e", "AebAbort"),
                ],
            },
            {
                "label": "SteerAngle",
                "height_px": 70,
                "unit": "deg",
                "series": [
                    (
                        "steerWheelAngle",
                        "#12b886",
                        "SteerWheelAngle",
                        ["steerWheelAngleDeg", "steerWheelAngle"],
                    ),
                ],
            },
            {
                "label": "SteerAngleRate",
                "height_px": 70,
                "unit": "deg/s",
                "series": [
                    (
                        "steerWheelAngleSpeed",
                        "#20c997",
                        "SteerWheelAngleSpeed",
                        ["steerWheelAngleSpeedDeg", "steerWheelAngleSpeed"],
                    ),
                ],
            },
            {
                "label": "YawRate",
                "height_px": 70,
                "unit": "deg/s",
                "series": [
                    (
                        "yawRate",
                        "#fa5252",
                        "YawRate",
                        ["yawRateDeg", "yawRate"],
                    ),
                ],
            },
            {
                "label": "LatAccel",
                "height_px": 70,
                "unit": "m/s2",
                "series": [
                    ("latActAccel", "#339af0", "LatActAccel"),
                ],
            },
            {
                "label": "BrakePedal",
                "height_px": 30,
                "unit": None,
                "series": [
                    ("brakePedalPressed", "#845ef7", "BrakePedalPressed"),
                ],
            },
            {
                "label": "Confidence",
                "height_px": 70,
                "unit": None,
                "series": [
                    ("obstConf", "#a64ac9", "ObstConf"),
                    ("posConf", "#e98b2a", "PosConf"),
                    ("velConf", "#1ca9c9", "VelConf"),
                ],
            },
        ]
    
    def __init__(self, out_dir: str):
        # Initialize with feature-specific signal candidates
        super().__init__(out_dir)
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
        self.bottom_row_height_px = 70
        self.bottom_row_gap_px = 2     # control per-row gaps
        self.bottom_min_height_px = 650
        self.bottom_legend_pad_px = 12
        self.bottom_legend_item_gap = -6 # configurable legend gap
        self.bottom_legend_gutter_px = 160
        self.bottom_legend_left_pct = 91 # increase to move legends rightward
        self.bottom_slider_height_px = 16
        self.bottom_slider_label_gap_px = 30
        self.bottom_slider_margin_px = 20
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
        return super()._build_fig_bottom(signals)



    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI", extra_traces=None):
        if extra_traces is None:
            extra_traces = []

        fig_top = self._build_fig_top(kpi_row, signals)
        grid_bottom = self._build_fig_bottom(signals)

        # ================================
        # COMBINE & SAVE
        # ================================
        html_top = pio.to_html(fig_top, include_plotlyjs="cdn", full_html=False)
        html_bottom = grid_bottom.render_embed()

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
