# src/viz/core/exporters.py
import os
import warnings

import matplotlib.pyplot as plt
import plotly.io as pio
from plotly.tools import mpl_to_plotly


class Exporter:
    """
    Handles conversion from Matplotlib → Plotly and legend ordering.
    """

    def __init__(self, out_path_output: str):
        self.out_path_output = out_path_output

    # ------------ main API ------------ #
    def export_html(
        self,
        fig,
        title: str,
        group_id: int,
        draw_labels,
        calibratables: dict,
        interactive: bool = False,
    ):
        out_name_html = f"Fig_{group_id:02d} - {title}.html"
        out_path_html = os.path.join(self.out_path_output, out_name_html)

        # Build ordering: calibratables + series + averages
        cal_key_map = {k.lower(): k for k in calibratables.keys()}
        calibratables_labels, series_labels, avg_labels = [], [], []

        for lbl in draw_labels:
            low = lbl.lower()
            if low in cal_key_map:
                calibratables_labels.append(cal_key_map[low])
            elif lbl.startswith("Average "):
                avg_labels.append(lbl)
            else:
                series_labels.append(lbl)

        # Optional: title-specific rules (copied from your old implementation)
        tl = str(title).lower()

        if "pedalpospro" in tl:
            prio = {
                "max throttle value": 0,
                "max throttle increase during aeb": 1,
            }
            series_labels.sort(key=lambda s: prio.get(s.lower(), 999))

        if "aeb braking distances" in tl:
            prio = {
                "first detection dist": 0,
                "stable detection dist": 1,
                "aeb actuation dist": 2,
                "aeb stop gap": 3,
            }
            series_labels.sort(key=lambda s: prio.get(s.lower(), 999))

            # reorder averages to follow their series
            ordered_avg = []
            for s in series_labels:
                match = next(
                    (a for a in avg_labels if a.startswith(f"Average {s}")),
                    None,
                )
                if match:
                    ordered_avg.append(match)
            avg_labels = ordered_avg

        desired_series = series_labels[:]
        desired_order = calibratables_labels + series_labels + avg_labels
        print(f"🌐 Exporting interactive HTML for '{title}' ...")

        try:
            plotly_fig = mpl_to_plotly(fig, strip_style=True)

            plotly_fig.layout.width = None
            plotly_fig.layout.height = None
            plotly_fig.update_layout(
                autosize=True,
                margin=dict(l=60, r=60, t=80, b=60),
                template="plotly_white",
                legend=dict(
                    x=0.98,
                    y=0.98,
                    xanchor="right",
                    yanchor="top",
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="lightgray",
                    borderwidth=1,
                ),
            )

            traces = list(plotly_fig.data)

            # Partition traces roughly by type
            scatter_traces = [
                t for t in traces if getattr(t, "mode", "") and "markers" in t.mode
            ]
            line_only_traces = [
                t
                for t in traces
                if getattr(t, "mode", "")
                and "lines" in t.mode
                and "markers" not in t.mode
            ]

            # Identify black dashed averages vs calibratables
            def _is_black(c):
                if c is None:
                    return False
                s = str(c).replace(" ", "").lower()
                return s.startswith("rgb(0,0,0)") or s.startswith("rgba(0,0,0")

            avg_line_traces, cal_line_traces = [], []
            for t in line_only_traces:
                lc = getattr(getattr(t, "line", None), "color", None)
                if _is_black(lc):
                    avg_line_traces.append(t)
                else:
                    cal_line_traces.append(t)

            # 1) Calibratables
            for t, lbl in zip(cal_line_traces, calibratables_labels):
                t.name = lbl

            # 2) KPI series
            for t, lbl in zip(scatter_traces, desired_series):
                t.name = lbl

            # 3) Averages
            for t, lbl in zip(avg_line_traces, avg_labels):
                t.name = lbl

            seen = set()
            for t in traces:
                nm = (getattr(t, "name", "") or "").strip()
                if nm and nm not in seen:
                    t.showlegend = True
                    seen.add(nm)
                else:
                    t.showlegend = False

            pio.write_html(
                plotly_fig,
                file=out_path_html,
                full_html=True,
                include_plotlyjs="cdn",
                auto_open=False,
                config={"responsive": True},
            )

            print(f"✅ Saved interactive HTML → {out_name_html}")
            print(f"🧭 Legend order used: {desired_order}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export Plotly HTML: {e}")
            png_path = os.path.join(
                self.out_path_output, f"Fig_{group_id:02d} - {title}.png"
            )
            fig.savefig(png_path, dpi=400, bbox_inches="tight")
            print(f"💾 Fallback PNG saved → {png_path}")

        if interactive:
            plt.show(block=True)
        else:
            plt.close(fig)
