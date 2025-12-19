# src/viz/core/exporters.py
import os
import warnings
from pathlib import Path
import base64
import json

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

        # Optional: title-specific rules 
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

        # Update combined index page so all figure HTMLs can be browsed in one place
        self._build_index(out_name_html, out_path_html)

    # ------------ helpers ------------ #
    def _build_index(self, new_name: str, new_path: str):
        """
        Generate a single HTML index that embeds all exported figure HTMLs and
        removes the individual files afterward. Uses an on-disk cache so
        multiple exports accumulate instead of overwriting.
        """
        out_dir = Path(self.out_path_output)
        cache_file = out_dir / "index_cache.json"
        entries = []

        if cache_file.exists():
            try:
                entries = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                entries = []

        # Read the newly created figure
        try:
            content = Path(new_path).read_text(encoding="utf-8")
            encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
            # replace or append
            entries = [e for e in entries if e.get("name") != new_name]
            entries.append({"name": new_name, "content": encoded})
        except Exception as exc:  # noqa: BLE001
            warnings.warn(f"⚠️ Failed to read {new_name} for index embed: {exc}")

        if not entries:
            return

        # sort for stable order
        entries.sort(key=lambda e: e.get("name", ""))

        sections = []
        nav_links = []
        for entry in entries:
            name = entry.get("name", "figure")
            fid = name.replace(" ", "_").replace(".", "_")
            nav_links.append(f'<a href="#{fid}">{name}</a>')
            encoded = entry.get("content", "")
            sections.append(
                f"""
                <section id="{fid}">
                    <h2>{name}</h2>
                    <iframe src="data:text/html;base64,{encoded}" loading="lazy"></iframe>
                </section>
                """
            )

        index_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>KPI Figures</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0 12px 24px 12px;
            background: #f8fafc;
        }}
        header {{
            position: sticky;
            top: 0;
            background: #f8fafc;
            padding: 12px 0;
            z-index: 10;
        }}
        nav {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        nav a {{
            text-decoration: none;
            color: #2563eb;
            padding: 4px 8px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            background: #fff;
        }}
        section {{
            margin-top: 18px;
        }}
        section h2 {{
            margin: 8px 0;
            font-size: 16px;
        }}
        iframe {{
            width: 100%;
            height: 75vh;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            background: #fff;
        }}
    </style>
</head>
<body>
    <header>
        <h1 style="margin:0 0 8px 0;">KPI Figures</h1>
        <nav>
            {' '.join(nav_links)}
        </nav>
    </header>
    {''.join(sections)}
</body>
</html>
"""

        index_path = out_dir / "index.html"
        index_path.write_text(index_html, encoding="utf-8")

        # Persist cache
        cache_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

        # Remove individual fig file now that it's embedded
        try:
            Path(new_path).unlink()
        except Exception:
            pass
