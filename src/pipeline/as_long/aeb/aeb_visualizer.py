import os
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from src.viz.visualizers.base_event_visualizer import BaseEventVisualizer
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
            "obstConf": ["obstConf"],
            "posConf": ["posConf"],
            "velConf": ["velConf"],
            "aebTargetType": ["aebTargetType"],
            "longGap": ["longGap"],
        }
        # Feature-specific layout defaults (override base if needed)
        self.layout_params = {
            "rows": 6,
            "cols": 3,
            "shared_xaxes": False,
            "column_widths": [0.45, 0.15, 0.40],
            "row_heights": [0.32, 0.16, 0.16, 0.16, 0.1, 0.1],
            # Row-1 gap control: increase to widen spacing between top plots.
            # Suggested range: 0.0–0.2 (will be clamped to Plotly's max spacing)
            "horizontal_spacing": 0.15,
            # Rows 2–6 gap control: 0 = no gap, higher values widen body columns.
            "body_horizontal_spacing": 0.0,
            "vertical_spacing": 0.04,
            # Figure margins (adjust these to affect apparent horizontal gaps)
            "margins": {"l": 0, "r": 0, "t": 60, "b": 8},
            "width": 1800,
        }
        self.interval_pad_before_sec = 1.0
        self.interval_pad_after_sec = 0.5
        self.interval_gap_merge_sec = 2.0
        enum_file = get_resource("config/enum_definitions.yaml")
        self.enum_mapper = EnumMapper(enum_file)

    def get_layout_params(self):
        """
        Customize the layout titles to be AEB specific.
        """
        return dict(self.layout_params)

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

    def plot_cycle(self, kpi_row, signals: dict, title: str = "Cycle KPI", extra_traces=None):
        if extra_traces is None:
            extra_traces = []

        time_arr = signals.get("time")
        long_gap = signals.get("longGap")
        intervals = self._compute_intervals(time_arr, long_gap)
        if not intervals and time_arr is not None:
            intervals = [(time_arr.min(), time_arr.max())]

        num_intervals = len(intervals)

        # ================================
        # TOP FIGURE: 3 fixed plots
        # ================================
        fig_top = make_subplots(
            rows=1, cols=3,
            subplot_titles=["Path (colored by speed)", "AEB Availability", "AEB Suppression Breakdown"],
            horizontal_spacing=0.08,
            column_widths=[0.45, 0.15, 0.40]
        )

        # Path
        lon = signals.get("lon")
        lat = signals.get("lat")
        spd = signals.get("speed")
        if lon is not None and lat is not None and spd is not None:
            fig_top.add_trace(go.Scatter(
                x=lon, y=lat,
                mode="lines+markers",
                marker=dict(size=5, color=spd, colorscale="Turbo", coloraxis="coloraxis"),
                line=dict(width=0.5, color="rgba(0,0,0,0.1)"),
                showlegend=False
            ), row=1, col=1)

        # Availability
        avail = kpi_row.get("AvailDistPct")
        if avail is not None:
            fig_top.add_trace(go.Bar(
                x=[""], y=[avail],
                marker_color="#4c6ef5",
                text=f"{avail:.1f}%",
                textposition="inside"
            ), row=1, col=2)
            fig_top.update_yaxes(range=[0, 100], title_text="Percent", row=1, col=2)

        # Suppression reasons
        reasons = {k: v for k, v in kpi_row.items() if "Suppression" in k or k == "LowSpeed"}
        if reasons:
            labels = [k.replace("Suppression", "").replace("PosPro", "Pedal") for k in reasons]
            values = list(reasons.values())
            fig_top.add_trace(go.Bar(
                x=values, y=labels,
                orientation="h",
                marker_color="#74c0fc",
                text=[f"{v:.1f}%" for v in values],
                textposition="inside"
            ), row=1, col=3)
            fig_top.update_yaxes(autorange="reversed", row=1, col=3)
            fig_top.update_xaxes(range=[0, 100], title_text="Percent", row=1, col=3)

        fig_top.update_layout(
            height=400,
            margin=dict(l=40, r=40, t=60, b=20),
            template="plotly_white",
            showlegend=False,
            coloraxis=dict(colorscale="Turbo", cmin=0, cmax=120,
                        colorbar=dict(title="Speed [kph]", x=0.46, len=0.6))
        )

        # ================================
        # BOTTOM FIGURE: Dynamic intervals (CORRECT ORDER!)
        # ================================
        if num_intervals == 0:
            fig_bottom = go.Figure()
            fig_bottom.add_annotation(
                text="No AEB intervals detected", x=0.5, y=0.5,
                xref="paper", yref="paper", showarrow=False, font_size=20
            )
            fig_bottom.update_layout(height=600, margin=dict(l=40, r=40, t=40, b=40))
        else:
            # === 1. Compute column widths FIRST ===
            if num_intervals > 1:
                base = [1.4] + [1.0] * (num_intervals - 1)
                total = sum(base)
                col_widths = [x / total for x in base]
            else:
                col_widths = [1.0]

            # === 2. Create fig_bottom ONCE with correct column_widths ===
            fig_bottom = make_subplots(
                rows=5,
                cols=num_intervals,
                shared_xaxes=True,
                vertical_spacing=0.04,
                horizontal_spacing=0.02,
                column_widths=col_widths,  # ← Now it's applied correctly
                subplot_titles=[f"Int {i+1}<br>{s:.1f}-{e:.1f}s"
                               for i, (s, e) in enumerate(intervals)]
            )

            # === 3. NOW add all traces (this was already correct) ===
            styles = [
                ("obstConf", "#a64ac9", "ObstConf"),
                ("posConf", "#e98b2a", "PosConf"),
                ("velConf", "#1ca9c9", "VelConf"),
                ("aebTargetType", "#c05a5a", "AEB Target Type"),
                ("longGap", "#7bb661", "LongGap"),
            ]

            for col_idx, (start, end) in enumerate(intervals, 1):
                mask = (time_arr >= start) & (time_arr <= end)
                t_seg = time_arr[mask]

                # Add all 5 traces for this interval
                for row_idx, (key, color, label) in enumerate(styles, 1):
                    data = signals.get(key)
                    if data is None or len(np.asarray(data)[mask]) == 0:
                        continue
                    y_seg = np.asarray(data)[mask]

                    if key == "aebTargetType":
                        texts = self._map_obstacle_class(y_seg)
                        fig_bottom.add_trace(go.Scatter(
                            x=t_seg, y=y_seg, mode="lines", line_color=color,
                            text=texts,
                            hovertemplate="t=%{x:.2f}s<br>%{text}<extra></extra>"
                        ), row=row_idx, col=col_idx)
                    else:
                        fig_bottom.add_trace(go.Scatter(
                            x=t_seg, y=y_seg, mode="lines", line_color=color, showlegend=False
                        ), row=row_idx, col=col_idx)

                # SET X-RANGE ONCE PER COLUMN — AFTER all rows are added
                for row_idx in range(1, 6):

                    fig_bottom.update_xaxes(range=[start, end], row=row_idx, col=col_idx)
                    # === Y-AXIS LABELS: Only on left-most column ===
                    y_labels = ["ObstConf", "PosConf", "VelConf", "AEB Target Type", "LongGap"]
                    for row_idx, label in enumerate(y_labels, start=1):
                        fig_bottom.update_yaxes(
                            title_text=label,
                            title_standoff=15,
                            title_font=dict(size=13),
                            tickfont=dict(size=11),
                            showgrid=True,
                            gridcolor="rgba(200,200,200,0.3)",
                            zeroline=False,
                            row=row_idx,
                            col=1
                        )

                    # Fixed range for confidence signals
                    for row_idx in [1, 2, 3]:
                        fig_bottom.update_yaxes(range=[0, 1], dtick=0.25, row=row_idx, col=1)

                    # Hide y-tick labels on all columns except the first
                    if num_intervals > 1:
                        for row_idx in range(1, 6):
                            for col_idx in range(2, num_intervals + 1):
                                fig_bottom.update_yaxes(showticklabels=False, row=row_idx, col=col_idx)

                    # Show x-axis labels only on the bottom row (LongGap)
                    for col_idx in range(1, num_intervals + 1):
                        fig_bottom.update_xaxes(showticklabels=True, row=5, col=col_idx)
                    for row_idx in range(1, 5):
                        for col_idx in range(1, num_intervals + 1):
                            fig_bottom.update_xaxes(showticklabels=False, row=row_idx, col=col_idx)

                    # Final layout polish
                    fig_bottom.update_layout(
                        height=620,
                        template="plotly_white",
                        showlegend=False,
                        margin=dict(l=90, r=30, t=60, b=50),
                    )

        # ================================
        # COMBINE & SAVE
        # ================================
        html_top = pio.to_html(fig_top, include_plotlyjs="cdn", full_html=False)
        html_bottom = pio.to_html(fig_bottom, include_plotlyjs=False, full_html=False)

        full_html = f"""
        <html><head><title>{title}</title></head>
        <body style="margin:0; padding:20px; background:#f9f9f9;">
            <h2 style="text-align:center; color:#1e3d73;">{title}</h2>
            {html_top}
            <div style="height:30px;"></div>
            {html_bottom}
        </body></html>
        """

        out_path = os.path.join(self.out_dir, f"{title.replace(' ', '_')}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"Cycle dashboard saved → {out_path}")

class AebEventVisualizer(BaseEventVisualizer):
    """AEB KPI visualizer routed through the shared viz module."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")
