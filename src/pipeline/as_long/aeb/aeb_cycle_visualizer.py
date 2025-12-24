import os

import numpy as np
import plotly.io as pio
from pyecharts import options as opts
from pyecharts.charts import Line, Grid
from pyecharts.commons.utils import JsCode

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
        if time_arr is None:
            raise ValueError("Missing 'time' signal")

        styles = [
            ("obstConf", "#a64ac9", "ObstConf"),
            ("posConf", "#e98b2a", "PosConf"),
            ("velConf", "#1ca9c9", "VelConf"),
            ("aebTargetType", "#c05a5a", "AEB Target Type"),
            ("longGap", "#7bb661", "LongGap"),
        ]

        grid = Grid(
            init_opts=opts.InitOpts(
                width="100%",
                height="650px",
                bg_color="#ffffff",
            )
        )

        row_gap = 2
        slider_space = 11
        available = 100 - slider_space - (len(styles) - 1) * row_gap
        row_height = max(available / len(styles), 5)

        x = np.asarray(time_arr, dtype=float).tolist()
        xaxis_indices = list(range(len(styles)))

        for idx, (key, color, label) in enumerate(styles):
            data = signals.get(key)
            if data is None:
                continue
            y_raw = np.asarray(data, dtype=float)
            y = [float(v) if np.isfinite(v) else None for v in y_raw.tolist()]

            # Special handling for enum hover
            if key == "aebTargetType":
                texts = self._map_obstacle_class(y)
                y_items = [
                    {"value": y[i], "name": texts[i] if texts else None}
                    for i in range(len(y))
                ]

                tooltip = opts.TooltipOpts(
                    trigger="axis",
                    formatter=JsCode(
                        """
                        function (params) {
                            var d = params[0].data || {};
                            return 't=' + params[0].axisValue.toFixed(2) + 's<br>' +
                                (d.name || '');
                        }
                        """
                    ),
                )
            else:
                tooltip = opts.TooltipOpts(trigger="axis")

            line = (
                Line()
                .add_xaxis(xaxis_data=x)
                .add_yaxis(
                    series_name=label,
                    y_axis=y_items if key == "aebTargetType" else y,
                    is_symbol_show=False,
                    linestyle_opts=opts.LineStyleOpts(color=color),
                )
                .set_global_opts(
                    tooltip_opts=tooltip,
                    xaxis_opts=opts.AxisOpts(
                        type_="value",
                        axislabel_opts=opts.LabelOpts(is_show=(idx == 4)),
                    ),
                    yaxis_opts=opts.AxisOpts(
                        min_=0 if idx < 3 else None,
                        max_=1.1 if idx < 3 else None,
                        name=label,
                        name_location="middle",
                        name_gap=45,
                    ),
                    legend_opts=opts.LegendOpts(is_show=False),
                    datazoom_opts=(
                        [
                            opts.DataZoomOpts(
                                type_="slider",
                                xaxis_index=xaxis_indices,
                                is_show_data_shadow=False,
                                is_show_detail=False,
                                pos_bottom="2%",
                                range_start=0,
                                range_end=100,
                            )
                        ]
                        if idx == len(styles) - 1
                        else None
                    ),
                )
            )

            top_pct = idx * (row_height + row_gap)

            grid.add(
                line,
                grid_opts=opts.GridOpts(
                    pos_left="80px",
                    pos_right="30px",
                    pos_top=f"{top_pct}%",
                    height=f"{row_height}%",
                ),
            )

        return grid



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
