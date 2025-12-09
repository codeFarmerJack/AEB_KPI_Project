import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class CycleVisualizer:
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
            rows=3,
            cols=1,
            shared_xaxes=False,
            row_heights=[0.25, 0.45, 0.3],
            subplot_titles=("Availability Summary", "Path (colored by speed)", "Signals"),
        )

        # 1) Availability summary (hierarchical)
        overall = kpi_row.get("AvailDistPct")
        breakdown_keys = [k for k in ["runSetting", "inputHealthy", "precondBlk", "abort"] if k in kpi_row]
        avail_values = [overall] + [kpi_row.get(k) for k in breakdown_keys]

        # Level 3 placeholders (precondition inputs) – reserve space, mark as TBD
        precond_inputs = ["Steering", "Throttle", "YawRate", "LatAccel"]
        precond_values = [None] * len(precond_inputs)

        # Multi-category axes: Level1 groups, Level2 items
        level1_avail = ["Availability"] * len(avail_values)
        level2_avail = ["AvailDistPct"] + breakdown_keys

        level1_pre = ["Precondition Inputs"] * len(precond_inputs)
        level2_pre = precond_inputs

        # Trace for availability hierarchy
        fig.add_trace(
            go.Bar(
                x=[level1_avail, level2_avail],
                y=avail_values,
                name="Availability [%]",
                marker=dict(
                    color=["#4c6ef5"] + ["#7c9dfb"] * len(breakdown_keys)
                ),
                texttemplate="%{y:.1f}%",
                textposition="auto",
            ),
            row=1,
            col=1,
        )

        # Trace for placeholder precondition drivers (shows hierarchy, reserved)
        fig.add_trace(
            go.Bar(
                x=[level1_pre, level2_pre],
                y=[0] * len(precond_inputs),
                name="Precond drivers (reserved)",
                marker=dict(
                    color="#d0d7e2",
                    line=dict(color="#94a3b8", width=1),
                    pattern=dict(shape="/", fgcolor="#94a3b8"),
                ),
                text=["TBD"] * len(precond_inputs),
                textposition="outside",
            ),
            row=1,
            col=1,
        )

        fig.add_annotation(
            text="AvailDistPct = runSetting ∧ inputHealthy ∧ precondBlk ∧ abort (placeholders for precond drivers)",
            xref="paper",
            yref="paper",
            x=0.01,
            y=1.08,
            showarrow=False,
            font=dict(size=10, color="#444"),
        )

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
                row=2,
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
                row=3,
                col=1,
            )

        # 4) Optional extra traces on the signals row
        if extra_traces:
            for tr in extra_traces:
                fig.add_trace(tr, row=3, col=1)

        fig.update_layout(
            title=title,
            template="plotly_white",
            height=900,
        )

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")
