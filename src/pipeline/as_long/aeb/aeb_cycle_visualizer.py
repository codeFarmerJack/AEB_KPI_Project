import os

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
                "height_px": 100,
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
                    ("aebFullState", "#3007fe", "AebFullState", {"cast": "int"}),
                    ("aebPartialState", "#ed0808", "AebPartialState", {"cast": "int"}),
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
                    ("aebPrecondBlkFromNdas", "#5c7cfa", "aebPrecondBlkFromNdas", {"cast": "int"}),
                    ("aebAbortFromNdas", "#f03e3e", "aebAbortFromNdas", {"cast": "int"}),
                ],
            },
            {
                "label": "SteerAngle",
                "height_px": 70,
                "unit": "deg",
                "series": [
                    ("steerWheelAngleDeg", "#12b886", "SteerWheelAngle"),
                ],
            },
            {
                "label": "SteerAngleRate",
                "height_px": 70,
                "unit": "deg/s",
                "series": [
                    ("steerWheelAngleSpeedDeg", "#20c997", "SteerWheelAngleSpeed"),
                ],
            },
            {
                "label": "YawRate",
                "height_px": 70,
                "unit": "deg/s",
                "series": [
                    ("yawRateDeg", "#fa5252", "YawRate"),
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
                    ("brakePedalPressed", "#845ef7", "BrakePedalPressed", {"cast": "int"}),
                ],
            },
        ]
    layout_top = {
        "rows": 1,
        "cols": 4,
        "column_widths": [0.30, 0.30, 0.20, 0.20],
        "horizontal_spacing": 0.06,
        "vertical_spacing": 0.00,
        "margins": {"l": 20, "r": 20, "t": 2, "b": 8},
    }
    fig_top_titles = [
        "Path (aeb-fb state)",
        "Path (aeb-pb state)",
        "AEB Availability",
        "AEB Suppression Breakdown",
    ]
    availability_defs = [
        ("Driver", "AvailDistPct", "#4c6ef5"),
        ("ROV", "ROVAvail", "#40c057"),
        ("VAL", "VALAvail", "#fab005"),
        ("No Degradation", "NoDegradation", "#15aabf"),
    ]
    suppression_patterns = [
        "SteeringWheelAngleRate",
        "SteeringWheelAngle",
        "PedalPosProSuppression",
        "LatAccel",
        "YawRate",
        "LowSpeed",
    ]
    state_colors = {
        "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_UNSPECIFIED": "#adb5bd",
        "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_READY": "#51cf66",
        "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_ACTIVE": "#ff6b6b",
        "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_HOLD": "#ffd43b",
        "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_UNAVAILABLE": "#868e96",
        "AUTO_EMERGENCY_BRAKING_PLANNER_STATE_DEGRADED": "#ffa94d",
    }
    path_subplot_defs = [
        {
            "col": 1,
            "signal_name": "aebFullState",
            "label_prefix": "aeb-fb",
        },
        {
            "col": 2,
            "signal_name": "aebPartialState",
            "label_prefix": "aeb-pb",
        },
    ]
    availability_col = 3
    suppression_col = 4
    default_state_color = "#adb5bd"
    state_defs = []
    bottom_row_height_px = 70
    bottom_row_gap_px = -2
    bottom_min_height_px = 650
    bottom_legend_pad_px = 12
    bottom_legend_item_gap = -6
    bottom_legend_gutter_px = 160
    bottom_legend_left_pct = 91
    bottom_slider_height_px = 16
    bottom_slider_label_gap_px = 30
    bottom_slider_margin_px = 20

    def __init__(self, out_dir: str):
        super().__init__(out_dir)
        self.html_gap_px = 5  # Vertical gap between top and bottom figures (px)

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



    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI"):

        fig_top = self._build_fig_top(kpi_row, signals)
        grid_bottom = self._build_fig_bottom(signals)

        # ================================
        # COMBINE & SAVE
        # ================================
        html_top = pio.to_html(fig_top, include_plotlyjs="cdn", full_html=False)
        html_bottom = self._render_bottom_with_cursor_panel(grid_bottom)
        cursor_css = self._cursor_panel_css()

        full_html = f"""
        <html><head><title>{title}</title><style>{cursor_css}</style></head>
        <body style="margin:0; padding:20px; background:#f9f9f9;">
            <h2 style="text-align:center; color:#1e3d73;">{title}</h2>
            {html_top}
            <div style="height:{self.html_gap_px}px;"></div>
            {html_bottom}
        </body></html>
        """

        safe_title = self._format_title_for_filename(title)
        out_path = os.path.join(self.out_dir, f"{safe_title}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"Cycle dashboard saved → {out_path}")
