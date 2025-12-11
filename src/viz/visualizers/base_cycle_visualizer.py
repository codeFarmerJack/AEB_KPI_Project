import os
import warnings
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.utils.signal_mdf import safe_load_mdf, get_signal


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
        # default mapping of logical signal names to candidate mdf channels
        self.signal_candidates = {
            "time": ["time"],
            "lon": ["longitude"],
            "lat": ["latitude"],
            "speed": ["egoSpeedKph"],
        }
        # default layout params (top row widths and spacing are user-tunable)
        self.top_column_widths = [0.55, 0.10, 0.35]
        self.top_horizontal_spacing = 0.13
        self.top_row_height = 0.6
        self.bottom_row_height = 0.4
        self.layout_params = dict(
            num_rows=2,
            num_cols=3,
            shared_xaxes=False,
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

    # ------------------------------------------------------------------ #
    # Overridable hooks
    # ------------------------------------------------------------------ #
    def get_layout_params(self):
        """
        Return kwargs for plotly.subplots.make_subplots.
        Subclasses can override to change layout (num_rows/num_cols/sizes/titles).
        """
        params = dict(self.layout_params)
        # Translate custom keys to plotly kwargs
        params["rows"] = params.pop("num_rows", params.get("rows", 2))
        params["cols"] = params.pop("num_cols", params.get("cols", 3))
        params["horizontal_spacing"] = self.top_horizontal_spacing
        params["column_widths"] = self.top_column_widths
        params["row_heights"] = [
            self.top_row_height,
            self.bottom_row_height,
        ]
        return params

    def prepare_signals(self, signals: dict) -> dict:
        """
        Hook to tweak/augment signals before plotting.
        Subclasses can override (e.g., unit conversion, custom keys).
        """
        return signals or {}

    def extract_cycle_signals(self, mdf):
        """
        Default signal extraction for cycle dashboards.
        Subclasses can override for feature-specific signals.
        """
        def pick(candidates):
            for c in candidates:
                try:
                    val = get_signal(mdf, c)
                    if val is not None:
                        return val
                except Exception:
                    continue
            return None

        candidates = self.signal_candidates

        return {key: pick(vals) for key, vals in candidates.items()}

    def plot_cycle(
        self,
        kpi_row,
        signals: dict,
        title: str = "Cycle KPI",
        extra_traces: list | None = None,
    ):
        # allow subclasses to control layout and signals
        layout_kwargs = self.get_layout_params()
        signals = self.prepare_signals(signals)

        fig = make_subplots(**layout_kwargs)

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
                    coloraxis="coloraxis",
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

        # 3) Time-series signals (speed)
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

        # If a coloraxis was used, position its colorbar beside the path subplot
        if speed is not None and lon is not None and lat is not None:
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

        fig.update_layout(
            title=title,
            template="plotly_white",
            height=750,
        )

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")

    # ------------------------------------------------------------------ #
    def render_dashboards(self, kpi_table, feature_name, in_path_extracted, signal_extractor=None):
        """
        Render dashboards for each row in the KPI table.

        Parameters
        ----------
        kpi_table : pd.DataFrame
            Cycle KPI table containing 'label' and 'feature' columns.
        feature_name : str
            Feature to filter num_rows by (e.g., 'AEB').
        in_path_extracted : str
            Directory where MF4 files are located.
        signal_extractor : callable, optional
            Function taking an MDF object and returning a signals dict for plotting.
            If None, uses self.extract_cycle_signals().
        """
        if kpi_table is None or kpi_table.empty:
            return

        extractor = signal_extractor or (lambda mdf: self.extract_cycle_signals(mdf))

        for _, row in kpi_table.iterrows():
            if str(row.get("feature", "")).strip().upper() != str(feature_name).strip().upper():
                continue

            label = str(row.get("label", "")).strip()
            if not label:
                continue

            fpath = os.path.join(in_path_extracted, label)
            if not os.path.exists(fpath):
                warnings.warn(f"⚠️ Cycle dashboard skipped — file not found: {fpath}")
                continue

            mdf = safe_load_mdf(fpath)
            if mdf is None:
                continue

            signals = extractor(mdf)
            title = f"{str(feature_name).upper()} - {Path(label).stem}"
            try:
                self.plot_cycle(row, signals, title=title)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to render cycle dashboard for {label}: {e}")
