import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.viz.visualizers.base_event_visualizer import BaseEventVisualizer
from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer
from src.utils.signal_mdf import get_signal
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
        }
        # Feature-specific layout defaults (override base if needed)
        self.layout_params = {
            "rows": 5,
            "cols": 3,
            "shared_xaxes": False,
            "column_widths": [0.45, 0.18, 0.37],
            "row_heights": [0.5, 0.125, 0.125, 0.125, 0.125],
            "specs": [
                [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
                [{"type": "xy", "colspan": 3}, None, None],
                [{"type": "xy", "colspan": 3}, None, None],
                [{"type": "xy", "colspan": 3}, None, None],
                [{"type": "xy", "colspan": 3}, None, None],
            ],
            "subplot_titles": (
                "AEB Path (colored by speed)",
                "AEB Availability",
                "AEB Suppression Breakdown",
                "ObstConf",
                "PosConf",
                "VelConf",
                "AEB Target Type",
            ),
        }
        enum_file = get_resource("config/enum_definitions.yaml")
        self.enum_mapper = EnumMapper(enum_file)

    def get_layout_params(self):
        """
        Customize the layout titles to be AEB specific.
        """
        return dict(self.layout_params)

    def prepare_signals(self, signals: dict) -> dict:
        """
        Convert speed to kph if provided (plot coloring expects 0–120 kph).
        """
        prepared = super().prepare_signals(signals)
        if prepared is None:
            return prepared
        speed = prepared.get("speed")
        if speed is not None:
            try:
                prepared["speed"] = np.asarray(speed, dtype=float) * 3.6
            except Exception:
                pass
        return prepared

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
        """
        layout_kwargs = self.get_layout_params()
        signals = self.prepare_signals(signals)
        fig = make_subplots(**layout_kwargs)

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

        def add_line(row, series, name):
            if series is None or signals.get("time") is None:
                return
            fig.add_trace(
                go.Scatter(x=signals["time"], y=series, mode="lines", name=name),
                row=row,
                col=1,
            )

        add_availability()
        spd_for_colorbar = add_path()
        add_line(2, signals.get("obstConf"), "ObstConf")
        add_line(3, signals.get("posConf"), "PosConf")
        add_line(4, signals.get("velConf"), "VelConf")
        obst_type = signals.get("aebTargetType")
        if obst_type is not None and signals.get("time") is not None:
            labels = self._map_obstacle_class(obst_type)
            fig.add_trace(
                go.Scatter(
                    x=signals["time"],
                    y=obst_type,
                    mode="lines",
                    name="AEB Target Type",
                    text=labels,
                    hovertemplate="t=%{x:.2f}s<br>code=%{y}<br>type=%{text}<extra></extra>",
                ),
                row=5,
                col=1,
            )

        if extra_traces:
            for tr in extra_traces:
                fig.add_trace(tr, row=2, col=1)

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

        fig.update_layout(title=title, template="plotly_white", height=1000)
        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")


class AebEventVisualizer(BaseEventVisualizer):
    """AEB KPI visualizer routed through the shared viz module."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")
