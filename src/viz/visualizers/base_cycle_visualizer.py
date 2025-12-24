import os
import warnings
from pathlib import Path

import numpy as np
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
        # interval handling defaults (can be overridden in subclasses)
        self.interval_pad_before_sec = 1.0
        self.interval_pad_after_sec = 0.5
        self.interval_gap_merge_sec = 2.0
        # default layout params 
        self.layout_params = {
            "rows": 2,
            "cols": 3,
            "shared_xaxes": False,
            "column_widths": [0.55, 0.10, 0.35],
            "row_heights": [0.6, 0.4],
            "horizontal_spacing": 0.13,
            "vertical_spacing": 0.05,
            "margins": {"l": 40, "r": 40, "t": 60, "b": 40},
            "specs": [
                [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
                [{"type": "xy", "colspan": 3}, None, None],
            ],
            "subplot_titles": (
                "Path (colored by speed)",
                "Availability",
                "Suppression Breakdown",
                "Signals",
            ),
        }

    # ------------------------------------------------------------------ #
    # Overridable hooks
    # ------------------------------------------------------------------ #
    def get_layout_params(self):
        """
        Return kwargs for plotly.subplots.make_subplots.
        Subclasses can override to change layout (num_rows/num_cols/sizes/titles).
        """
        return dict(self.layout_params)

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

    def _compute_intervals(self, time_arr, target_arr):
        """Return list of (start,end) intervals where target_arr is non-zero, merging short gaps."""
        if time_arr is None or target_arr is None:
            return []
        t = np.asarray(time_arr, dtype=float)
        tid = np.nan_to_num(np.asarray(target_arr, dtype=float), nan=0.0)
        if len(t) == 0:
            return []
        nonzero = tid != 0
        merged = nonzero.copy()
        i = 0
        while i < len(t):
            if not merged[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(t) and merged[j + 1]:
                j += 1
            k = j + 1
            while k < len(t) and not merged[k]:
                k += 1
            if k < len(t):
                gap = t[k] - t[j]
                if gap < self.interval_gap_merge_sec:
                    merged[j + 1 : k] = True
                    i = k
                    continue
            i = j + 1
        starts = np.where(merged & ~np.roll(merged, 1))[0]
        ends = np.where(merged & ~np.roll(merged, -1))[0]
        intervals = []
        for s, e in zip(starts, ends):
            intervals.append(
                (
                    t[s] - self.interval_pad_before_sec,
                    t[e] + self.interval_pad_after_sec,
                )
            )
        return intervals

    def _compute_offset_path(self, lon, lat, offset_scale=0.02, min_offset=1e-6):
        def _smooth_series(values, window=5):
            if window < 2 or len(values) < window:
                return values
            kernel = np.ones(window, dtype=float) / float(window)
            return np.convolve(values, kernel, mode="same")

        def _fill_vector_gaps(dx, dy, eps=1e-9):
            mag = np.hypot(dx, dy)
            valid = mag > eps
            if valid.all():
                return dx, dy
            idx = np.arange(len(dx))
            if valid.any():
                last = idx[valid][0]
                for i in range(last + 1, len(dx)):
                    if valid[i]:
                        last = i
                    else:
                        dx[i] = dx[last]
                        dy[i] = dy[last]
                first = idx[valid][0]
                for i in range(first - 1, -1, -1):
                    dx[i] = dx[first]
                    dy[i] = dy[first]
            else:
                dx[:] = 1.0
                dy[:] = 0.0
            return dx, dy

        lon_arr = np.asarray(lon, dtype=float)
        lat_arr = np.asarray(lat, dtype=float)
        if lon_arr.size == 0 or lat_arr.size == 0:
            return None
        mask = np.isfinite(lon_arr) & np.isfinite(lat_arr)
        if not mask.any():
            return None
        finite_lon = lon_arr[mask]
        finite_lat = lat_arr[mask]
        idx = np.arange(lon_arr.size)
        lon_filled = lon_arr.copy()
        lat_filled = lat_arr.copy()
        if not np.isfinite(lon_filled).all():
            lon_filled[~np.isfinite(lon_filled)] = np.interp(
                idx[~np.isfinite(lon_filled)],
                idx[np.isfinite(lon_filled)],
                lon_filled[np.isfinite(lon_filled)],
            )
        if not np.isfinite(lat_filled).all():
            lat_filled[~np.isfinite(lat_filled)] = np.interp(
                idx[~np.isfinite(lat_filled)],
                idx[np.isfinite(lat_filled)],
                lat_filled[np.isfinite(lat_filled)],
            )
        span = max(finite_lon.max() - finite_lon.min(), finite_lat.max() - finite_lat.min())
        if not np.isfinite(span) or span == 0:
            span = 1.0
        offset = max(span * offset_scale, min_offset)

        cx = finite_lon.mean()
        cy = finite_lat.mean()
        lon_smooth = _smooth_series(lon_filled, window=7)
        lat_smooth = _smooth_series(lat_filled, window=7)
        dx = np.gradient(lon_smooth)
        dy = np.gradient(lat_smooth)
        dx, dy = _fill_vector_gaps(dx, dy)
        mag = np.hypot(dx, dy)
        mag[mag == 0] = 1.0
        nx = -dy / mag
        ny = dx / mag
        for i in range(1, len(nx)):
            if nx[i] * nx[i - 1] + ny[i] * ny[i - 1] < 0:
                nx[i] = -nx[i]
                ny[i] = -ny[i]
        vx = lon_filled - cx
        vy = lat_filled - cy
        if np.nanmean(nx * vx + ny * vy) < 0:
            nx = -nx
            ny = -ny
        return lon_filled + nx * offset, lat_filled + ny * offset

    def plot_cycle(
        self,
        kpi_row,
        signals: dict,
        title: str = "Cycle KPI",
        extra_traces: list | None = None,
    ):
        # allow subclasses to control layout and signals
        layout_kwargs = dict(self.get_layout_params())
        # Strip non-plotly keys for make_subplots
        margins = layout_kwargs.pop("margins", None)
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
            reason_labels = list(reason_keys)
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
        if margins:
            fig.update_layout(margin=margins)

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
        print(f"💾 Cycle dashboard saved → {out_path}")

    # ------------------------------------------------------------------ #
    def render_dashboards(self, kpi_table, feature_name, in_path_extracted):
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
        """
        if kpi_table is None or kpi_table.empty:
            return

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

            signals = self.extract_cycle_signals(mdf)
            title = f"{str(feature_name).upper()} - {Path(label).stem}"
            try:
                self.plot_cycle(row, signals, title=title)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to render cycle dashboard for {label}: {e}")
