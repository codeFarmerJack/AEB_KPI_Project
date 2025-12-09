import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class BaseCycleVisualizer:
    """
    Simple dashboard-style visualizer for cycle KPIs.
    Expects:
      - kpi_row: single-row Series or dict of KPI values
      - signals: dict-like with 'time', 'lon', 'lat', etc.
    """

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def plot_cycle(
        self,
        kpi_row,
        signals: dict,
        title: str = "Cycle KPI",
        extra_traces: list | None = None,
    ):
        fig = make_subplots(
            rows=2,
            cols=3,
            shared_xaxes=False,
            column_widths=[0.45, 0.18, 0.37],
            row_heights=[0.55, 0.45],
            specs=[
                [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
                [{"type": "xy", "colspan": 3}, None, None],
            ],
            subplot_titles=(
                "Path (colored by speed)",
                "Availability",
                "Suppression Breakdown",
                "Signals",
            ),
        )

        # 1) Availability + suppression reasons (mixed orientation)
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

        # 2) Path colored by speed
        lon   = signals.get("lon")
        lat   = signals.get("lat")
        speed = signals.get("speed")

        if lon is not None and lat is not None:
            marker_kwargs = dict(size=5)
            if speed is not None:
                marker_kwargs.update(
                    color=speed,
                    colorscale="Turbo",
                    cmin=0,
                    cmax=120,
                    colorbar=dict(title="Speed [kph]"),
                )
            fig.add_trace(
                go.Scatter(
                    x=lon,
                    y=lat,
                    mode="markers",
                    name="Path",
                    marker=marker_kwargs,
                ),
                row=1,
                col=1,
            )

        # 3) Time-series signals (example: speed)
        time = signals.get("time")
        if time is not None and speed is not None:
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=speed,
                    mode="lines",
                    name="Speed",
                ),
                row=2,
                col=1,
            )

        # 4) Optional extra traces on the signals row
        if extra_traces:
            for tr in extra_traces:
                fig.add_trace(tr, row=2, col=1)

        fig.update_layout(
            title=title,
            template="plotly_white",
            height=750,
        )

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")

