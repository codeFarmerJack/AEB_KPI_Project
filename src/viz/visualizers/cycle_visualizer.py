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

    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI"):
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=False,
            row_heights=[0.25, 0.35, 0.4],
            subplot_titles=("KPI Summary", "Path", "Signals"),
        )

        # 1) KPI bar chart
        keys = list(kpi_row.keys())
        vals = [kpi_row[k] for k in keys]
        fig.add_trace(
            go.Bar(x=keys, y=vals, name="KPIs"),
            row=1,
            col=1,
        )

        # 2) Path colored by availability (if provided)
        lon = signals.get("lon")
        lat = signals.get("lat")
        avail = signals.get("avail")

        if lon is not None and lat is not None:
            marker_kwargs = dict(size=6)
            if avail is not None:
                marker_kwargs["color"] = avail
                marker_kwargs["colorscale"] = ["red", "green"]
                marker_kwargs["colorbar"] = dict(title="Avail")
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
        speed = signals.get("speed")
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

        fig.update_layout(
            title=title,
            template="plotly_white",
            height=900,
        )

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")
