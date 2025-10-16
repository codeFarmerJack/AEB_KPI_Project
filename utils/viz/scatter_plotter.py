import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import plotly.io as pio
from plotly.tools import mpl_to_plotly
from collections import defaultdict

class ScatterPlotter:

    def __init__(self, obj):
        self.graph_spec      = obj.graph_spec
        self.line_colors     = obj.line_colors
        self.marker_shapes   = self._extract_marker_shapes(obj.marker_shapes)
        self.calibratables   = obj.calibratables
        self.kpi_spec        = obj.kpi_spec
        self.kpi_data        = obj.kpi_data
        self.path_to_output  = obj.path_to_output
        self.interactive     = getattr(obj, "interactive", False)
        self._fig_cache      = {}
        self._group_counter  = getattr(obj, "_group_counter", iter(range(1, 100)))
        self._series_labels  = defaultdict(list)   
        self._draw_labels    = defaultdict(list)  # authoritative draw-order ledger

    # ==========================================================
    # Public API
    # ==========================================================
    def plot(self, graph_idx):
        """Main entry point — plot one graph by index."""
        data = self.kpi_data
        if not isinstance(data, pd.DataFrame) or data.empty:
            warnings.warn("⚠️ kpi_data is empty or invalid — cannot plot.")
            return

        # --- Extract metadata ---
        title = self.graph_spec.loc[graph_idx, "title"]
        same_title_rows = self.graph_spec.index[self.graph_spec["title"] == title].tolist()
        enabled_rows = [r for r in same_title_rows if self._is_row_enabled(self.graph_spec.loc[r, "plotenabled"])]

        if not enabled_rows:
            print(f"⚠️ Skipping '{title}' — no enabled rows.")
            return

        first_row, last_row = enabled_rows[0], enabled_rows[-1]
        is_first, is_last   = graph_idx == first_row, graph_idx == last_row

        # === Initialize or reuse figure === #
        if title not in self._fig_cache:
            fig, ax = plt.subplots(figsize=(9, 6))
            ax.set_title(title)
            ax.grid(True, which="both", linestyle="--", alpha=0.5)
            x_var   = str(self.graph_spec.loc[0, "reference"])
            x_label = str(self.graph_spec.loc[0, "axis_name"])
            ax.set_xlim(
                float(self.graph_spec.loc[0, "min_axis_value"]),
                float(self.graph_spec.loc[0, "max_axis_value"]),
            )
            ax.set_xlabel(x_label.replace("_", " "))
            self._fig_cache[title] = (fig, ax)
            print(f"🆕 Created figure for '{title}'")
        else:
            fig, ax = self._fig_cache[title]
            print(f"🔁 Reusing existing figure for '{title}'")

        # === Plot current Y === #
        y_var         = str(self.graph_spec.loc[graph_idx, "reference"])
        y_label       = str(self.graph_spec.loc[graph_idx, "axis_name"])
        legend_name   = str(self.graph_spec.loc[graph_idx, "legend"])
        connect_flag  = self._resolve_connect_flag(self.graph_spec.loc[graph_idx, "connectpoints"])
        avg_flag      = str(self.graph_spec.loc[graph_idx, "average"]).strip().lower() == "true"
        ax.set_ylabel(y_label.replace("_", " "))

        self._series_labels[title].append(legend_name)

        if is_first:
            y_min = float(self.graph_spec.loc[first_row, "min_axis_value"])
            y_max = float(self.graph_spec.loc[first_row, "max_axis_value"])
            ax.set_ylim(y_min, y_max)

        row_in_group  = same_title_rows.index(graph_idx)
        marker, color = self._select_marker_and_color(row_in_group)

        x_var_global  = str(self.graph_spec.loc[0, "reference"])
        var_names     = self.kpi_spec["name"].astype(str).tolist()
        display_names = [
            f"{row['name']} [{row['unit']}]" if pd.notna(row.get("unit")) else str(row["name"])
            for _, row in self.kpi_spec.iterrows()
        ]
        x_col, y_col = self._resolve_xy_columns(x_var_global, y_var, var_names, display_names)

        if not x_col or not y_col:
            return

        filt_mask = self._resolve_filter(self.graph_spec.loc[graph_idx, "plotenabled"])
        x_vals    = data.loc[filt_mask, x_col].to_numpy()
        y_vals    = data.loc[filt_mask, y_col].to_numpy()

        if connect_flag:
            ax.plot(x_vals, y_vals, linestyle="-", marker=marker, color=color, label=legend_name)
        else:
            ax.scatter(x_vals, y_vals, marker=marker, color=color, label=legend_name)

        self._draw_labels[title].append(legend_name)     # <-- record


        # Add average line if enabled
        if avg_flag and len(y_vals) > 0:
            y_avg = float(np.nanmean(y_vals))
            x_min, x_max = ax.get_xlim()
            avg_label = f"Average {legend_name}: {y_avg:.3f}"

            ax.plot([x_min, x_max], [y_avg, y_avg], "--",
                    color="black", linewidth=1.2, alpha=0.7,
                    label=avg_label, zorder=5)
            self._draw_labels[title].append(avg_label)   # <-- record
            print(f"➕ Added average line for '{legend_name}' at y={y_avg:.3f}")

        # === Finalize if last in group === #
        if is_last:
            self._finalize_figure(title, fig, ax, enabled_rows)

    # ==========================================================
    # Internal helpers
    # ==========================================================
    def _extract_marker_shapes(self, marker_df):
        if isinstance(marker_df, pd.DataFrame):
            col_candidates = [c for c in marker_df.columns if c.strip().lower() == "shapes"]
            if col_candidates:
                shape_col = col_candidates[0]
                shapes = marker_df[shape_col].dropna().astype(str).str.strip().tolist()
            else:
                shapes = ['o', 's', '^', 'D']
        elif isinstance(marker_df, (list, tuple)):
            shapes = list(marker_df)
        else:
            shapes = ['o', 's', '^', 'D']
        return shapes or ['o']

    def _resolve_xy_columns(self, x_var, y_var, var_names, display_names):
        def clean(s): return s.lower().replace(" ", "").replace("[", "").replace("]", "")
        cols = [clean(c) for c in self.kpi_data.columns]
        mapping = dict(zip(cols, self.kpi_data.columns))
        x_col = mapping.get(clean(x_var)) or next((v for c, v in mapping.items() if clean(x_var) in c), None)
        y_col = mapping.get(clean(y_var)) or next((v for c, v in mapping.items() if clean(y_var) in c), None)
        if not x_col or not y_col:
            warnings.warn(f"⚠️ X ({x_var}) or Y ({y_var}) not found in KPI data")
        return x_col, y_col

    def _is_row_enabled(self, val):
        val_str = str(val).strip().lower()
        if val_str == "true": return True
        if val_str in ["false", "na", "none", ""]: return False
        return True

    def _resolve_filter(self, plot_enabled):
        val = str(plot_enabled).strip()
        low = val.lower()
        if low == "true":
            return pd.Series(True, index=self.kpi_data.index)
        if low in ["false", "na", "none", ""]:
            return pd.Series(False, index=self.kpi_data.index)
        if val not in self.kpi_data.columns:
            warnings.warn(f"⚠️ Conditional flag '{val}' not found; plotting all points.")
            return pd.Series(True, index=self.kpi_data.index)

        col = self.kpi_data[val]
        if col.dtype == bool:
            mask = col
        elif np.issubdtype(col.dtype, np.number):
            mask = col.fillna(0) != 0
        else:
            mask = col.astype(str).str.lower().isin(["true", "1", "yes", "y"])
        return mask.reindex(self.kpi_data.index, fill_value=False)

    def _select_marker_and_color(self, row_in_group):
        m_idx = row_in_group % len(self.marker_shapes)
        marker = self.marker_shapes[m_idx]
        if isinstance(self.line_colors, pd.DataFrame):
            rgb_cols = [c.strip().lower() for c in self.line_colors.columns]
            if all(col in rgb_cols for col in ["r", "g", "b"]):
                self.line_colors.columns = rgb_cols
                rgb_array = self.line_colors[["r", "g", "b"]].to_numpy(dtype=float)
                c_idx = row_in_group % len(rgb_array)
                color = tuple(rgb_array[c_idx])
            else:
                color = plt.cm.tab10(row_in_group % 10)
        elif isinstance(self.line_colors, (list, np.ndarray)):
            color = self.line_colors[row_in_group % len(self.line_colors)]
        else:
            color = plt.cm.tab10(row_in_group % 10)
        return marker, color

    def _resolve_connect_flag(self, cp_raw):
        if isinstance(cp_raw, (bool, int, float)):
            return bool(cp_raw)
        return str(cp_raw).strip().lower() in ["true", "1", "yes", "y"]

    def _add_calibration_limit(self, cal_limit, ax, title):
        if not cal_limit or str(cal_limit).lower() == "none":
            return
        cal_key = next((k for k in self.calibratables.keys() if k.lower() == cal_limit.lower()), None)
        if not cal_key:
            warnings.warn(f"⚠️ Calibration limit '{cal_limit}' not found.")
            return
        lim = self.calibratables[cal_key]
        if not (isinstance(lim, dict) and "x" in lim and "y" in lim):
            warnings.warn(f"⚠️ Calibration {cal_limit} found but not in (x,y) format.")
            return

        ax.plot(lim["x"], lim["y"], "r--", linewidth=1.5, label=f"{cal_key}")
        self._draw_labels[title].append(str(cal_key))   # <-- record
        ax.relim(); ax.autoscale_view()


    def _finalize_figure(self, title, fig, ax, enabled_rows):
        # 1) Draw calibrations (they also get recorded into _draw_labels)
        for row in enabled_rows:
            cal_limit = str(self.graph_spec.loc[row, "calibration_lim"]).strip().lower()
            if cal_limit not in ["none", "nan", ""]:
                self._add_calibration_limit(cal_limit, ax, title)

        # Matplotlib legend (visual only)
        handles, labels = ax.get_legend_handles_labels()
        if labels:
            ax.legend(fontsize=8, loc="upper right")

        group_id = next(self._group_counter)
        out_name_html = f"Fig_{group_id:02d} - {title}.html"
        out_path_html = os.path.join(self.path_to_output, out_name_html)

        # ---------------- Build desired labels from the ledger ----------------
        raw = list(self._draw_labels.get(title, []))  # exact order of how you drew things

        cal_key_map = {k.lower(): k for k in self.calibratables.keys()}
        calibratables, series_labels, avg_labels = [], [], []

        for lbl in raw:
            low = lbl.lower()
            if low in cal_key_map:
                calibratables.append(cal_key_map[low])
            elif lbl.startswith("Average "):
                avg_labels.append(lbl)  # Average <series>: <value>
            else:
                series_labels.append(lbl)

        # ---- Title-specific ordering rules ----
        tl = str(title).lower()

        # FIGURE 03 rule (PedalPosPro*): Calibratable first, then Star=Max Throttle Value,
        # then Triangle=Max throttle increase during AEB
        if "pedalpospro" in tl:
            prio = {
                "max throttle value": 0,
                "max throttle increase during aeb": 1,
            }
            series_labels.sort(key=lambda s: prio.get(s.lower(), 999))

        # FIGURE 08 rule (AEB Braking Distances): ★ First, ▲ Stable, ◆ Actuation, ● Stop gap
        if "aeb braking distances" in tl:
            prio = {
                "first detection dist": 0,
                "stable detection dist": 1,
                "aeb actuation dist": 2,
                "aeb stop gap": 3,
            }
            series_labels.sort(key=lambda s: prio.get(s.lower(), 999))

            # Keep each average next to its series (if present)
            ordered_avg = []
            for s in series_labels:
                # find matching "Average <s>"
                match = next((a for a in avg_labels if a.startswith(f"Average {s}")), None)
                if match:
                    ordered_avg.append(match)
            avg_labels = ordered_avg  # only averages that match the sorted order

        # Final desired order: calibratables first (for Fig 03), then series, then their averages
        desired_series = series_labels[:]  # keep copy
        desired = calibratables + series_labels + avg_labels

        # ---------------- Convert → Plotly & assign by trace type ----------------
        print(f"🌐 Exporting interactive HTML for '{title}' ...")
        try:
            plotly_fig = mpl_to_plotly(fig, strip_style=True)

            # Responsive layout
            plotly_fig.layout.width = None
            plotly_fig.layout.height = None
            plotly_fig.update_layout(
                autosize=True,
                margin=dict(l=60, r=60, t=80, b=60),
                template="plotly_white",
                legend=dict(
                    x=0.98, y=0.98,
                    xanchor="right", yanchor="top",
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="lightgray", borderwidth=1
                ),
            )

            traces = list(plotly_fig.data)

            # Partition traces by type
            scatter_traces = [t for t in traces if getattr(t, "mode", "") and "markers" in t.mode]
            line_only_traces = [t for t in traces if getattr(t, "mode", "") and "lines" in t.mode and "markers" not in t.mode]

            # Identify average (black dashed) vs calibratable (remaining line-only)
            def _is_black(c):
                if c is None: return False
                s = str(c).replace(" ", "").lower()
                return s.startswith("rgb(0,0,0)") or s.startswith("rgba(0,0,0")

            avg_line_traces = []
            cal_line_traces = []
            for t in line_only_traces:
                lc = getattr(getattr(t, "line", None), "color", None)
                if _is_black(lc):
                    avg_line_traces.append(t)
                else:
                    cal_line_traces.append(t)

            # Assign names deterministically by type

            # 1) Calibratables
            for t, lbl in zip(cal_line_traces, calibratables):
                t.name = lbl

            # 2) Series (non-average) in your required order
            for t, lbl in zip(scatter_traces, desired_series):
                t.name = lbl

            # 3) Averages (black dashed) in the same order as desired_avg (built above)
            for t, lbl in zip(avg_line_traces, avg_labels):
                t.name = lbl

            # Ensure legend shows each entry once
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
            print(f"🧭 Legend order used: {desired}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export Plotly HTML: {e}")
            png_path = os.path.join(self.path_to_output, f"Fig_{group_id:02d} - {title}.png")
            fig.savefig(png_path, dpi=400, bbox_inches="tight")
            print(f"💾 Fallback PNG saved → {png_path}")

        # Cleanup
        if self.interactive:
            plt.show(block=True)
        else:
            plt.close(fig)
            print("💾 Non-interactive mode: figure saved only.")

        self._fig_cache.pop(title, None)
        self._series_labels.pop(title, None)
        self._draw_labels.pop(title, None)

