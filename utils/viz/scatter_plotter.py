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
    """
    MATLAB-equivalent grouped scatter plotter (class version).
    Each instance manages plotting configuration, figure caching,
    and export (PNG + interactive HTML).
    """

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
        self._series_labels  = defaultdict(list)  # track legend labels per title

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

    def _add_calibration_limit(self, cal_limit, ax):
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
        ax.relim()
        ax.autoscale_view()

    def _finalize_figure(self, title, fig, ax, enabled_rows):
        """Finalize figure export and cleanup."""
        # Add calibration limits first (these bring their own legend labels)
        for row in enabled_rows:
            cal_limit = str(self.graph_spec.loc[row, "calibration_lim"]).strip().lower()
            if cal_limit not in ["none", "nan", ""]:
                self._add_calibration_limit(cal_limit, ax)

        # De-duplicate legend (matplotlib side) so we export a clean structure
        if ax.get_legend_handles_labels()[1]:
            ax.legend(fontsize=8, loc="upper right")

        group_id = next(self._group_counter)
        out_name_html = f"Fig_{group_id:02d} - {title}.html"
        out_path_html = os.path.join(self.path_to_output, out_name_html)

        print(f"🌐 Exporting interactive HTML for '{title}' ...")
        try:
            # ---- Matplotlib -> Plotly ----
            plotly_fig = mpl_to_plotly(fig, strip_style=True)

            # (1) RESPONSIVENESS: remove fixed sizing and enable autosize
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

            # (2) LEGENDS: rename non-calibration traces using recorded labels
            data_labels = list(self._series_labels.get(title, []))  # copy
            # map lower-case calibratable keys back to canonical key
            cal_key_map = {k.lower(): k for k in self.calibratables.keys()}

            # First pass: fix names
            for tr in plotly_fig.data:
                tname = getattr(tr, "name", None)
                tnamel = tname.lower() if isinstance(tname, str) else ""

                # If it already matches a calibration key (possibly modified by mpl_to_plotly), normalize its case
                if tnamel in cal_key_map:
                    tr.name = cal_key_map[tnamel]
                    continue

                # Otherwise assign the next data series label (scatter/stem line, etc.)
                if data_labels:
                    tr.name = data_labels.pop(0)

            # Second pass: show each legend entry once (avoid duplicates)
            seen = set()
            for tr in plotly_fig.data:
                nm = getattr(tr, "name", "") or ""
                if nm not in seen:
                    tr.showlegend = True
                    seen.add(nm)
                else:
                    tr.showlegend = False

            # Write responsive HTML (Plotly will stretch to container width)
            pio.write_html(
                plotly_fig,
                file=out_path_html,
                full_html=True,
                include_plotlyjs="cdn",
                auto_open=False,
                config={"responsive": True},  # key flag for auto-resize
            )
            print(f"✅ Saved interactive HTML → {out_name_html}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export Plotly HTML: {e}")
            png_path = os.path.join(self.path_to_output, f"Fig_{group_id:02d} - {title}.png")
            fig.savefig(png_path, dpi=400, bbox_inches="tight")
            print(f"💾 Fallback PNG saved → {png_path}")

        if self.interactive:
            plt.show(block=True)
        else:
            plt.close(fig)
            print(f"💾 Non-interactive mode: figure saved only.")

        # Clear per-title caches
        if title in self._fig_cache:
            del self._fig_cache[title]
        if title in self._series_labels:
            del self._series_labels[title]

