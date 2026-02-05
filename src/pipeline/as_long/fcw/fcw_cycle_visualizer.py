import os

import plotly.io as pio

from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer
from src.utils.enum_loader import EnumMapper
from src.utils.path_manager import get_resource


class FcwCycleVisualizer(BaseCycleVisualizer):
    """Feature-specific cycle visualizer for FCW."""
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
            "label": "LongActAccel",
            "height_px": 100,
            "unit": "m/s2",
            "y_range": (-12, 1),
            "series": [
                ("longActAccel", "#2f9e44", "LongActAccel"),
            ],
        },
        {
            "label": "FCW State",
            "height_px": 40,
            "unit": None,
            "series": [
                ("fcwState", "#3007fe", "FcwState", {"cast": "int"}),
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
                ("fcwPrecondBlkFromNdas", "#5c7cfa", "fcwPrecondBlkFromNdas", {"cast": "int"}),
                ("fcwAbortFromNdas", "#f03e3e", "fcwAbortFromNdas", {"cast": "int"}),
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
        "cols": 3,
        "column_widths": [0.45, 0.25, 0.30],
        "horizontal_spacing": 0.10,
        "vertical_spacing": 0.00,
        "margins": {"l": 20, "r": 20, "t": 2, "b": 8},
    }
    fig_top_titles = [
        "Path (fcw state)",
        "FCW Availability",
        "FCW Suppression Breakdown",
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
        "FORWARD_COLLISION_WARNING_PLANNER_STATE_UNSPECIFIED": "#adb5bd",
        "FORWARD_COLLISION_WARNING_PLANNER_STATE_READY": "#51cf66",
        "FORWARD_COLLISION_WARNING_PLANNER_STATE_ACTIVE": "#ff6b6b",
        "FORWARD_COLLISION_WARNING_PLANNER_STATE_UNAVAILABLE": "#868e96",
        "FORWARD_COLLISION_WARNING_PLANNER_STATE_DEGRADED": "#ffa94d",
    }
    path_subplot_defs = [
        {
            "col": 1,
            "signal_name": "fcwState",
            "label_prefix": "fcw",
        },
    ]
    default_state_color = "#adb5bd"
    state_defs = []
    bottom_row_height_px = 70
    bottom_row_gap_px = -2
    bottom_min_height_px = 650
    bottom_legend_pad_px = 12
    bottom_legend_item_gap = 0
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

        html = f"""
        <html>
          <head>
            <meta charset="UTF-8"/>
            <title>{title}</title>
            <style>
              body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f8f9fa;
              }}
              .figure {{
                background: white;
                padding: 10px;
              }}
              .spacer {{
                height: {self.html_gap_px}px;
              }}
              {cursor_css}
            </style>
          </head>
          <body>
            <div class="figure">{html_top}</div>
            <div class="spacer"></div>
            <div class="figure">{html_bottom}</div>
          </body>
        </html>
        """

        safe_title = self._format_title_for_filename(title)
        out_path = os.path.join(self.out_dir, f"{safe_title}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"💾 Cycle dashboard saved → {out_path}")
