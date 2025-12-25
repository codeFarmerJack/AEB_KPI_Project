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
            "aebPrecondBlk": ["aebPrecondBlk"],
            "aebAbort": ["aebAbort"],
            "egoSpeedKph": ["egoSpeedKph"],
            "throttleValue": ["throttleValue"],
            "longActAccel": ["longActAccel"],
            "aebTargetDecel": ["aebTargetDecel"],
            "brakePedalPressed": ["brakePedalPressed"],
            "steerWheelAngle": ["steerWheelAngleDeg"],
            "steerWheelAngleSpeed": ["steerWheelAngleSpeedDeg"],
            "yawRate": ["yawRateDeg"],
            "latActAccel": ["latActAccel"],
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
        self.bottom_row_height_px = 70
        self.bottom_row_heights_px = {
            "Confidence": 70,
            "Precond/Abort": 20,
            "AEB State": 40,
            "EgoSpeedKph": 70,
            "Throttle": 70,
            "Accel/TargetDecel": 70,
            "BrakePedal": 20,
            "SteerAngle": 70,
            "SteerAngleRate": 70,
            "YawRate": 70,
            "LatAccel": 70,
            "LongGap": 70,
        }
        self.bottom_row_gap_px = 16
        self.bottom_min_height_px = 650
        self.bottom_legend_pad_px = 12
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
        time_arr = signals.get("time")
        if time_arr is None:
            raise ValueError("Missing 'time' signal")

        row_defs = [
            {
                "label": "Confidence",
                "series": [
                    ("obstConf", "#a64ac9", "ObstConf"),
                    ("posConf", "#e98b2a", "PosConf"),
                    ("velConf", "#1ca9c9", "VelConf"),
                ],
                "y_range": (0, 1.1),
            },
            {
                "label": "Precond/Abort",
                "series": [
                    ("aebPrecondBlk", "#5c7cfa", "AebPrecondBlk"),
                    ("aebAbort", "#f03e3e", "AebAbort"),
                ],
                "y_range": (0, 1.1),
            },
            {
                "label": "AEB State",
                "series": [
                    ("aebFullState", "#40c057", "AebFullState"),
                    ("aebPartialState", "#15aabf", "AebPartialState"),
                ],
                "y_range": (0, 6),
            },
            {
                "label": "EgoSpeedKph",
                "series": [
                    ("egoSpeedKph", "#4c6ef5", "EgoSpeedKph"),
                ],
            },
            {
                "label": "Throttle",
                "series": [
                    ("throttleValue", "#ffa94d", "ThrottleValue"),
                ],
                "y_range": (0, 100),
            },
            {
                "label": "Accel/TargetDecel",
                "series": [
                    ("longActAccel", "#2f9e44", "LongActAccel"),
                    ("aebTargetDecel", "#d9480f", "AebTargetDecel"),
                ],
                "y_range": (-12, 1),
            },
            {
                "label": "BrakePedal",
                "series": [
                    ("brakePedalPressed", "#845ef7", "BrakePedalPressed"),
                ],
                "y_range": (0, 1.1),
            },
            {
                "label": "SteerAngle",
                "series": [
                    ("steerWheelAngle", "#12b886", "SteerWheelAngle"),
                ],
                "y_range": (-500, 500),
            },
            {
                "label": "SteerAngleRate",
                "series": [
                    ("steerWheelAngleSpeed", "#20c997", "SteerWheelAngleSpeed"),
                ],
                "y_range": (-500, 500),
            },
            {
                "label": "YawRate",
                "series": [
                    ("yawRate", "#fa5252", "YawRate"),
                ],
                "y_range": (-50, 50),
            },
            {
                "label": "LatAccel",
                "series": [
                    ("latActAccel", "#339af0", "LatActAccel"),
                ],
            },
            {
                "label": "LongGap",
                "series": [
                    ("longGap", "#7bb661", "LongGap"),
                ],
                "y_range": (0, 20),
            },
        ]

        def _to_float_list(values):
            out = []
            for v in np.asarray(values):
                try:
                    f = float(v)
                except Exception:
                    out.append(None)
                    continue
                out.append(f if np.isfinite(f) else None)
            return out

        active_rows = []
        for row in row_defs:
            series_data = []
            for key, color, label in row["series"]:
                data = signals.get(key)
                if data is None:
                    continue
                series_data.append(
                    {
                        "label": label,
                        "color": color,
                        "y": _to_float_list(data),
                    }
                )
            if series_data:
                active_rows.append(
                    {
                        "label": row["label"],
                        "series": series_data,
                        "y_range": row.get("y_range"),
                        "height_px": row.get("height_px"),
                    }
                )

        row_gap_px = self.bottom_row_gap_px
        legend_pad_px = self.bottom_legend_pad_px
        slider_space_px = (
            self.bottom_slider_height_px
            + self.bottom_slider_label_gap_px
            + self.bottom_slider_margin_px
        )

        for row in active_rows:
            if row["height_px"] is None:
                row["height_px"] = self.bottom_row_heights_px.get(
                    row["label"],
                    self.bottom_row_height_px,
                )

        rows_total_px = sum(row["height_px"] for row in active_rows)
        grid_height = max(
            self.bottom_min_height_px,
            int(
                rows_total_px + (len(active_rows) - 1) * row_gap_px
                + slider_space_px
            ),
        )
        grid = Grid(
            init_opts=opts.InitOpts(
                width="100%",
                height=f"{grid_height}px",
                bg_color="#ffffff",
            )
        )

        if not active_rows:
            return grid

        row_gap = row_gap_px / grid_height * 100
        slider_space = slider_space_px / grid_height * 100
        legend_pad = legend_pad_px / grid_height * 100
        slider_bottom_pct = (self.bottom_slider_margin_px / grid_height) * 100
        scale = (100 - slider_space - (len(active_rows) - 1) * row_gap) / max(
            rows_total_px,
            1,
        )

        x = np.asarray(time_arr, dtype=float).tolist()
        xaxis_indices = list(range(len(active_rows)))
        axis_pointer = opts.AxisPointerOpts(
            is_show=True,
            link=[{"xAxisIndex": "all"}],
            is_snap=True,
            is_trigger_tooltip=True,
            label=opts.LabelOpts(is_show=False),
        )
        tooltip = opts.TooltipOpts(
            trigger="axis",
            axis_pointer_type="line",
            is_show_content=False,
            formatter=JsCode("function () { return ''; }"),
            background_color="rgba(0,0,0,0)",
            border_width=0,
            padding=0,
            extra_css_text="box-shadow:none;",
        )
        value_label = opts.LabelOpts(
            is_show=True,
            formatter=JsCode(
                """
                function (params) {
                    var d = params.data;
                    var v = d;
                    if (d && typeof d === 'object') {
                        if (d.name !== undefined && d.name !== null && d.name !== '') {
                            v = d.name;
                        } else if (d.value !== undefined) {
                            v = d.value;
                        }
                    }
                    if (Array.isArray(v)) {
                        v = v[v.length - 1];
                    }
                    if (typeof v === 'number') {
                        v = v.toFixed(3);
                    }
                    return v;
                }
                """
            ),
        )

        top_pct = 0.0

        for idx, row in enumerate(active_rows):
            line = Line().add_xaxis(xaxis_data=x)

            for series in row["series"]:
                line = line.add_yaxis(
                    series_name=series["label"],
                    y_axis=series["y"],
                    is_symbol_show=False,
                    symbol="none",
                    symbol_size=0,
                    label_opts=opts.LabelOpts(is_show=False),
                    emphasis_opts=opts.EmphasisOpts(label_opts=value_label),
                    linestyle_opts=opts.LineStyleOpts(color=series["color"]),
                )

            y_min, y_max = None, None
            if row.get("y_range"):
                y_min, y_max = row["y_range"]

            row_height = row["height_px"] * scale
            plot_height = max(row_height - legend_pad, 1)

            legend_orient = "vertical" if len(row["series"]) > 1 else "horizontal"
            legend_opts = opts.LegendOpts(
                is_show=True,
                orient=legend_orient,
                pos_right="3%",
                pos_top=f"{top_pct + 0.1}%",
                item_gap=0,
                item_width=28,
                item_height=2,
                legend_icon="rect",
                textstyle_opts=opts.TextStyleOpts(font_size=10),
            )

            yaxis_kwargs = {
                "name": "",
                "axispointer_opts": opts.AxisPointerOpts(
                    is_show=False,
                    label=opts.LabelOpts(is_show=False),
                ),
                "split_number": 4,
            }

            if y_min is not None and y_max is not None:
                yaxis_kwargs.update(min_=y_min, max_=y_max)

            datazoom = opts.DataZoomOpts(
                type_="slider",
                xaxis_index=xaxis_indices,
                pos_bottom=f"{slider_bottom_pct:.2f}%",
                is_show_data_shadow=False,
                is_show_detail=False,
                range_start=0,
                range_end=100,
            )
            datazoom.opts["height"] = self.bottom_slider_height_px

            line = line.set_global_opts(
                tooltip_opts=tooltip,
                xaxis_opts=opts.AxisOpts(
                    type_="value",
                    axislabel_opts=opts.LabelOpts(
                        is_show=(idx == len(active_rows) - 1)
                    ),
                    axispointer_opts=opts.AxisPointerOpts(
                        is_show=True,
                        label=opts.LabelOpts(is_show=False),
                    ),
                ),
                yaxis_opts=opts.AxisOpts(**yaxis_kwargs),
                legend_opts=legend_opts,
                axispointer_opts=axis_pointer,
                datazoom_opts=(
                    [datazoom]
                    if idx == len(active_rows) - 1
                    else None
                ),
            )

            grid.add(
                line,
                grid_opts=opts.GridOpts(
                    pos_left="80px",
                    pos_right="30px",
                    pos_top=f"{top_pct + legend_pad}%",
                    height=f"{plot_height}%",
                ),
            )

            top_pct += row_height + row_gap

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
