import os
import warnings
import pandas as pd
import numpy as np
import matplotlib

# --- Configure Matplotlib backend (safe for macOS & virtualenvs) ---
try:
    matplotlib.use("TkAgg")  # Preferred for interactive plots
except Exception:
    matplotlib.use("MacOSX")  # Fallback for native macOS GUI backend

import matplotlib.pyplot as plt
import plotly.io as pio
from plotly.tools import mpl_to_plotly


def scatter_plotter(obj, graph_idx):
    """
    MATLAB-equivalent grouped scatter plotter.
    Combines multiple rows with same Title into one figure.

    Notes
    -----
    This version assumes that all KPI data are already loaded
    into obj.kpi_data (from Excel or CSV beforehand).
    No file I/O occurs here.
    """

    # --- Core inputs ---
    graph_spec      = obj.graph_spec
    line_colors     = obj.line_colors.values if isinstance(obj.line_colors, pd.DataFrame) else obj.line_colors
    marker_shapes   = _extract_marker_shapes(obj.marker_shapes)
    calibratables   = obj.calibratables
    kpi_spec        = obj.kpi_spec
    data            = obj.kpi_data

    if not isinstance(data, pd.DataFrame) or data.empty:
        warnings.warn("⚠️ kpi_data is empty or invalid — cannot plot.")
        return

    # --- KPI variable names ---
    var_names       = kpi_spec["name"].astype(str).tolist()
    display_names   = [
        f"{row['name']} [{row['unit']}]" if pd.notna(row.get("unit")) else str(row["name"])
        for _, row in kpi_spec.iterrows()
    ]

    # --- Group by Title ---
    title           = graph_spec.loc[graph_idx, "title"]
    same_title_rows = graph_spec.index[graph_spec["title"] == title].tolist()
    enabled_rows    = [
        r for r in same_title_rows
        if str(graph_spec.loc[r, "plotenabled"]).strip().lower() not in ["false", "na", ""]
    ]
    if not enabled_rows:
        print(f"⚠️ Skipping '{title}' — no enabled rows.")
        return

    first_row, last_row = enabled_rows[0], enabled_rows[-1]
    is_first, is_last   = graph_idx == first_row, graph_idx == last_row

    # --- Skip disabled row ---
    plot_enabled = str(graph_spec.loc[graph_idx, "plotenabled"]).strip().lower()
    if plot_enabled in ["false", "na", ""]:
        return

    # === Initialize or reuse figure === #
    if title not in obj._fig_cache:
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.set_title(title)
        ax.grid(True, which="both", linestyle="--", alpha=0.5)
        # X-axis: always from row 0 (vehSpd)
        x_var   = str(graph_spec.loc[0, "reference"])
        x_label = str(graph_spec.loc[0, "axis_name"])
        ax.set_xlim(
            float(graph_spec.loc[0, "min_axis_value"]),
            float(graph_spec.loc[0, "max_axis_value"]),
        )
        ax.set_xlabel(x_label.replace("_", " "))
        obj._fig_cache[title] = (fig, ax)
        print(f"🆕 Created figure for '{title}'")
    else:
        fig, ax = obj._fig_cache[title]
        print(f"🔁 Reusing existing figure for '{title}'")

    # === Current variable === #
    y_var         = str(graph_spec.loc[graph_idx, "reference"])
    y_label       = str(graph_spec.loc[graph_idx, "axis_name"])
    cal_limit     = str(graph_spec.loc[graph_idx, "calibration_lim"])
    legend_name   = str(graph_spec.loc[graph_idx, "legend"])
    connect_flag  = _resolve_connect_flag(graph_spec.loc[graph_idx, "connectpoints"])

    ax.set_ylabel(y_label.replace("_", " "))

    # --- Set Y range only when first figure is created ---
    if is_first:
        y_min = float(graph_spec.loc[first_row, "min_axis_value"])
        y_max = float(graph_spec.loc[first_row, "max_axis_value"])
        ax.set_ylim(y_min, y_max)

    row_in_group  = same_title_rows.index(graph_idx)
    marker, color = _select_marker_and_color(marker_shapes, line_colors, same_title_rows, row_in_group)

    # --- Resolve X/Y columns ---
    x_var_global = str(graph_spec.loc[0, "reference"])
    x_col, y_col = _resolve_xy_columns(x_var_global, y_var, var_names, display_names, data, "in-memory KPI data")
    if not x_col or not y_col:
        return

    # --- Filter (if needed) ---
    filt_mask = _resolve_filter(plot_enabled, data, "in-memory KPI data")
    x_vals = data.loc[filt_mask, x_col].to_numpy()
    y_vals = data.loc[filt_mask, y_col].to_numpy()

    print(f"📈 {title} → {legend_name}: {len(x_vals)} points")

    if len(x_vals) == 0 or len(y_vals) == 0:
        return

    if connect_flag:
        ax.plot(x_vals, y_vals, linestyle="-", marker=marker, color=color, label=legend_name)
    else:
        ax.scatter(x_vals, y_vals, marker=marker, color=color, label=legend_name)

    # === Finalize figure === #
    if is_last:
        for row in enabled_rows:
            group_cal_limit = str(graph_spec.loc[row, "calibration_lim"]).strip().lower()
            if group_cal_limit not in ["none", "nan", ""]:
                _add_calibration_limit(group_cal_limit, calibratables, ax)
        if ax.get_legend_handles_labels()[1]:
            ax.legend(fontsize=8, loc="upper right")

        # --- Output paths ---
        try:
            group_id = next(obj._group_counter)
        except AttributeError:
            if not hasattr(obj, '_group_id'):
                obj._group_id = 0
            obj._group_id += 1
            group_id = obj._group_id

        out_name = f"Fig_{group_id:02d} - {title}.png"
        out_name_html = f"Fig_{group_id:02d} - {title}.html"
        out_path = os.path.join(obj.path_to_results, out_name)
        out_path_html = os.path.join(obj.path_to_results, out_name_html)

        # --- Export to interactive HTML ---
        try:
            print(f"🌐 Exporting interactive HTML for '{title}' ...")
            plotly_fig = mpl_to_plotly(fig, strip_style=True)
            plotly_fig.layout.width = None
            plotly_fig.layout.height = None
            plotly_fig.update_layout(autosize=True)

            # Assign legend names properly
            data_labels = [str(graph_spec.loc[row, "legend"]) for row in enabled_rows]
            cal_key_map = {k.lower(): k for k in calibratables.keys()}
            data_idx = 0
            for tr in plotly_fig.data:
                tname = getattr(tr, "name", None)
                tnamel = tname.lower() if isinstance(tname, str) else None
                if isinstance(tname, str) and tnamel in cal_key_map:
                    tr.name = cal_key_map[tnamel]
                    continue
                if isinstance(tname, str) and tname in data_labels:
                    data_labels.remove(tname)
                    continue
                if data_idx < len(data_labels):
                    tr.name = data_labels[data_idx]
                    data_idx += 1
            seen = set()
            for tr in plotly_fig.data:
                nm = getattr(tr, "name", "")
                tr.showlegend = nm not in seen
                seen.add(nm)
            plotly_fig.update_layout(
                margin=dict(l=60, r=60, t=80, b=60),
                font=dict(size=14),
                legend=dict(
                    x=0.98, y=0.98,
                    xanchor="right", yanchor="top",
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="lightgray", borderwidth=1
                ),
                template="plotly_white",
                autosize=True
            )
            pio.write_html(
                plotly_fig,
                file=out_path_html,
                full_html=True,
                include_plotlyjs="cdn",
                config={"responsive": True},
                auto_open=False,
            )
            print(f"✅ Saved interactive HTML → {out_name_html}")
        except Exception as e:
            import traceback
            warnings.warn(f"⚠️ Failed to export Plotly HTML: {e}")
            traceback.print_exc()
            fig.savefig(out_path, dpi=400, bbox_inches="tight")
            print(f"💾 Fallback PNG saved → {out_name}")

        # --- Show or close ---
        if getattr(obj, "interactive", False):
            print("🧭 Interactive mode: opening figure window...")
            plt.show(block=True)
        else:
            plt.close(fig)
            print(f"💾 Non-interactive mode: figure saved only.")

        if title in obj._fig_cache:
            del obj._fig_cache[title]
        print(f"✅ Saved merged figure for '{title}' → {out_name}")


# ---------------------------------------------------------------------- #
# Helper Functions
# ---------------------------------------------------------------------- #
def _extract_marker_shapes(marker_df):
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



def _resolve_xy_columns(x_var, y_var, var_names, display_names, data, source):
    def clean(s):
        return s.lower().replace(" ", "").replace("[", "").replace("]", "")
    cols = [clean(c) for c in data.columns]
    mapping = dict(zip(cols, data.columns))
    x_col = mapping.get(clean(x_var)) or next((v for c, v in mapping.items() if clean(x_var) in c), None)
    y_col = mapping.get(clean(y_var)) or next((v for c, v in mapping.items() if clean(y_var) in c), None)
    if not x_col or not y_col:
        warnings.warn(f"⚠️ X ({x_var}) or Y ({y_var}) not found in {source}")
    return x_col, y_col


def _resolve_filter(plot_enabled, data, source):
    pe = str(plot_enabled).strip().lower()
    if pe in ["true", "na", "none", ""]:
        return pd.Series(True, index=data.index)
    elif pe == "false":
        return pd.Series(False, index=data.index)
    if pe not in data.columns:
        return pd.Series(True, index=data.index)
    col = data[pe]
    if col.dtype == bool:
        mask = col
    elif col.dtype.kind in "iufc":
        mask = pd.notna(col) & (col != 0)
    else:
        mask = col.astype(str).str.lower().isin(["true", "1", "yes", "y"])
    return mask.astype(bool).reindex(data.index, fill_value=False)


def _select_marker_and_color(marker_shapes, line_colors, group_rows, row_in_group):
    m_idx = row_in_group % len(marker_shapes)
    marker = marker_shapes[m_idx]
    if isinstance(line_colors, pd.DataFrame):
        rgb_cols = [c.strip().lower() for c in line_colors.columns]
        if all(col in rgb_cols for col in ["r", "g", "b"]):
            line_colors.columns = rgb_cols
            rgb_array = line_colors[["r", "g", "b"]].to_numpy(dtype=float)
            c_idx = row_in_group % len(rgb_array)
            color = tuple(rgb_array[c_idx])
        else:
            warnings.warn("⚠️ line_colors sheet missing R/G/B columns — using default palette.")
            color = plt.cm.tab10(row_in_group % 10)
    elif isinstance(line_colors, (list, np.ndarray)):
        c_idx = row_in_group % len(line_colors)
        color = line_colors[c_idx]
    else:
        color = plt.cm.tab10(row_in_group % 10)
    return marker, color


def _resolve_connect_flag(cp_raw):
    if isinstance(cp_raw, (bool, int, float)):
        return bool(cp_raw)
    return str(cp_raw).strip().lower() in ["true", "1", "yes", "y"]


def _add_calibration_limit(cal_limit, calibratables, ax):
    if not cal_limit or str(cal_limit).lower() == "none":
        return
    cal_key = next((k for k in calibratables.keys() if k.lower() == cal_limit.lower()), None)
    if not cal_key:
        warnings.warn(f"⚠️ Calibration limit '{cal_limit}' not found.")
        return
    lim = calibratables[cal_key]
    if not (isinstance(lim, dict) and "x" in lim and "y" in lim):
        warnings.warn(f"⚠️ Calibration {cal_limit} found but not in (x,y) format.")
        return
    existing_labels = [lbl.get_text() for lbl in ax.get_legend().get_texts()] if ax.get_legend() else []
    if cal_key not in existing_labels:
        ax.plot(lim["x"], lim["y"], "r--", linewidth=1.5, label=f"{cal_key}")
        ax.relim()
        ax.autoscale_view()
