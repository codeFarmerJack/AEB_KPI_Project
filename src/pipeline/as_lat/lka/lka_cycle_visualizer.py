import os

import plotly.io as pio

from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer
from src.utils.enum_loader import EnumMapper
from src.utils.path_manager import get_resource


class LkaCycleVisualizer(BaseCycleVisualizer):
    """Feature-specific cycle visualizer for LKA."""
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
            "label": "LKA Intervention",
            "height_px": 40,
            "unit": None,
            "series": [
                ("lkaInterventionStatus", "#7950f2", "LkaInterventionStatus", {"cast": "int"}),
            ],
        },
        {
            "label": "DTLE / Target",
            "height_px": 70,
            "unit": "m",
            "series": [
                ("dtle", "#1864ab", "DTLE"),
                ("dtleTarget", "#4dabf7", "DTLETarget"),
            ],
        },
        {
            "label": "Rate Of Departure",
            "height_px": 70,
            "unit": None,
            "series": [
                ("rateOfDeparture", "#12b886", "RateOfDeparture"),
            ],
        },
        {
            "label": "Steer Torque",
            "height_px": 70,
            "unit": "Nm",
            "series": [
                ("steerWheelTorque", "#e8590c", "SteerWheelTorque"),
            ],
        },
        {
            "label": "Steer Angle",
            "height_px": 70,
            "unit": "deg",
            "series": [
                ("steerWheelAngleDeg", "#20c997", "SteerWheelAngle"),
            ],
        },
        {
            "label": "Curvature",
            "height_px": 70,
            "unit": None,
            "series": [
                ("vehCurvature", "#fab005", "VehCurvature"),
                ("laneCurvature", "#ffd43b", "LaneCurvature"),
            ],
        },
        {
            "label": "Ready / Block / Abort",
            "height_px": 40,
            "unit": None,
            "series": [
                ("lkaReadyLeft", "#4c6ef5", "ReadyLeft", {"cast": "int"}),
                ("lkaReadyRight", "#40c057", "ReadyRight", {"cast": "int"}),
                ("lkaPrecondBlk", "#5c7cfa", "PrecondBlk", {"cast": "int"}),
                ("lkaAbort", "#f03e3e", "Abort", {"cast": "int"}),
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
        "Path (colored by speed)",
        "LKA Availability",
        "LKA Suppression Breakdown",
    ]
    availability_defs = [
        ("Left", "AvailDistPctLeft", "#4c6ef5"),
        ("Right", "AvailDistPctRight", "#40c057"),
    ]
    suppression_patterns = []
    state_colors = {
        "DI_ACTIVE_SAFETY_EVENT_NONE": "#adb5bd",
        "DI_ACTIVE_SAFETY_EVENT_LEVEL_1": "#74c0fc",
        "DI_ACTIVE_SAFETY_EVENT_LEVEL_2": "#4c6ef5",
        "DI_ACTIVE_SAFETY_EVENT_LEVEL_3": "#ffa94d",
        "DI_ACTIVE_SAFETY_EVENT_LEVEL_4": "#fa5252",
    }
    default_state_color = "#adb5bd"
    state_defs = [
        {
            "signal_name": "lkaInterventionStatus",
            "label_prefix": "lka",
            "offset_scale": 0.010,
        },
    ]
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

    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI"):
        fig_top = self._build_fig_top(kpi_row, signals)
        grid_bottom = self._build_fig_bottom(signals)

        html_top = pio.to_html(fig_top, include_plotlyjs="cdn", full_html=False)
        html_bottom = grid_bottom.render_embed()

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
