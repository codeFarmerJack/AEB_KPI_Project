import os
import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def scatter_plotter(obj, graph_idx):
    """
    MATLAB-equivalent grouped scatter plotter.
    Combines multiple rows with same Title into one figure.
    """

    graph_spec = obj.graph_spec
    line_colors = obj.line_colors.values if isinstance(obj.line_colors, pd.DataFrame) else obj.line_colors
    marker_shapes = _extract_marker_shapes(obj.marker_shapes)
    calibratables = _apply_calibrations(obj.calibratables)
    path_to_csv = obj.path_to_chunks  # Output dir
    kpi_spec = obj.kpi_spec

    if not os.path.isdir(path_to_csv):
        warnings.warn(f"⚠️ Invalid path_to_csv: {path_to_csv}")
        return

    # --- KPI variable names ---
    var_names = kpi_spec["name"].astype(str).tolist()
    display_names = [
        f"{row['name']} [{row['unit']}]" if pd.notna(row.get("unit")) else str(row["name"])
        for _, row in kpi_spec.iterrows()
    ]

    # --- Group by Title ---
    title = graph_spec.loc[graph_idx, "title"]
    same_title_rows = graph_spec.index[graph_spec["title"] == title].tolist()
    enabled_rows = [
        r for r in same_title_rows
        if str(graph_spec.loc[r, "plotenabled"]).strip().lower() not in ["false", "na", ""]
    ]
    if not enabled_rows:
        print(f"⚠️ Skipping '{title}' — no enabled rows.")
        return

    first_row, last_row = enabled_rows[0], enabled_rows[-1]
    is_first, is_last = graph_idx == first_row, graph_idx == last_row

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
        x_var = str(graph_spec.loc[0, "reference"])
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
    y_var = str(graph_spec.loc[graph_idx, "reference"])
    y_label = str(graph_spec.loc[graph_idx, "axis_name"])
    cal_limit = str(graph_spec.loc[graph_idx, "calibration_lim"])
    legend_name = str(graph_spec.loc[graph_idx, "legend"])
    connect_flag = _resolve_connect_flag(graph_spec.loc[graph_idx, "connectpoints"])

    ax.set_ylabel(y_label.replace("_", " "))

    # --- Set Y range only when first figure is created ---
    if is_first:
        y_min = float(graph_spec.loc[first_row, "min_axis_value"])
        y_max = float(graph_spec.loc[first_row, "max_axis_value"])
        ax.set_ylim(y_min, y_max)

    row_in_group = same_title_rows.index(graph_idx)
    marker, color = _select_marker_and_color(marker_shapes, line_colors, same_title_rows, row_in_group)

    # === Iterate CSV files (assuming single CSV as per logs) === #
    csv_files = [os.path.join(path_to_csv, f) for f in os.listdir(path_to_csv) if f.lower().endswith(".csv")]
    if not csv_files:
        warnings.warn(f"⚠️ No CSV files found in {path_to_csv}")
        return

    for csv_file in csv_files:
        try:
            data = pd.read_csv(csv_file)
            if 'Unnamed: 0' in data.columns:
                data = data.drop(columns=['Unnamed: 0'])
            data = data.reset_index(drop=True)
        except Exception as e:
            warnings.warn(f"⚠️ Failed to read {csv_file}: {e}")
            continue

        # Resolve columns robustly
        x_col, y_col = _resolve_xy_columns(
            str(graph_spec.loc[0, "reference"]),
            y_var, var_names, display_names, data, csv_file
        )
        if not x_col or not y_col:
            continue

        # Apply filter if defined
        plot_enabled_col = str(graph_spec.loc[graph_idx, "plotenabled"]).strip()
        filt_mask = _resolve_filter(plot_enabled_col, data, csv_file)

        # Extract arrays
        x_vals = data.loc[filt_mask, x_col].to_numpy()
        y_vals = data.loc[filt_mask, y_col].to_numpy()

        print(f"📈 {os.path.basename(csv_file)} → {legend_name}: {len(x_vals)} points")

        if len(x_vals) == 0 or len(y_vals) == 0:
            continue

        if connect_flag:
            ax.plot(x_vals, y_vals, linestyle="-", marker=marker, color=color, label=legend_name)
        else:
            ax.scatter(x_vals, y_vals, marker=marker, color=color, label=legend_name)

    # === Save only once per group === #
    if is_last:
        # ✅ FIX: Add calibration limits for ALL enabled rows in the group (not just last)
        for row in enabled_rows:
            group_cal_limit = str(graph_spec.loc[row, "calibration_lim"]).strip().lower()
            if group_cal_limit not in ["none", "nan", ""]:
                _add_calibration_limit(group_cal_limit, calibratables, ax)
        if ax.get_legend_handles_labels()[1]:
            ax.legend(fontsize=8, loc="upper right")
        # ✅ Use group counter for sequential ID starting from 1
        try:
            group_id = next(obj._group_counter)
        except AttributeError:
            # Fallback if not initialized
            if not hasattr(obj, '_group_id'):
                obj._group_id = 0
            obj._group_id += 1
            group_id = obj._group_id
        out_name = f"Fig_{group_id:02d} - {title}.png"
        out_path = os.path.join(path_to_csv, out_name)
        fig.savefig(out_path, dpi=400, bbox_inches="tight")
        plt.close(fig)
        if title in obj._fig_cache:
            del obj._fig_cache[title]
        print(f"✅ Saved merged figure for '{title}' → {out_name}")

# =============== Helper Functions =============== #

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


def _apply_calibrations(calibratables):
    if "PedalPosProIncrease_Th" in calibratables:
        lim = calibratables["PedalPosProIncrease_Th"]
        if isinstance(lim, dict) and "y" in lim:
            calibratables["PedalPosProIncrease_Th"]["y"] = [v * 100 for v in lim["y"]]
    return calibratables


def _resolve_xy_columns(x_var, y_var, var_names, display_names, data, filename):
    def clean(s):
        return s.lower().replace(" ", "").replace("[", "").replace("]", "")
    cols = [clean(c) for c in data.columns]
    mapping = dict(zip(cols, data.columns))
    x_col = mapping.get(clean(x_var)) or next((v for c, v in mapping.items() if clean(x_var) in c), None)
    y_col = mapping.get(clean(y_var)) or next((v for c, v in mapping.items() if clean(y_var) in c), None)
    if not x_col or not y_col:
        warnings.warn(f"⚠️ X ({x_var}) or Y ({y_var}) not found in {filename}")
    return x_col, y_col


def _resolve_filter(plot_enabled, data, filename):
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
    """
    Select marker shape and RGB color for plotting.
    Accepts a DataFrame from Excel ('lineColors' sheet) with columns [R, G, B].
    """
    # --- Handle marker shapes ---
    m_idx = row_in_group % len(marker_shapes)
    marker = marker_shapes[m_idx]

    # --- Handle line colors ---
    if isinstance(line_colors, pd.DataFrame):
        # Normalize columns and ensure [R, G, B] exist
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
        # Already a list of RGB tuples
        c_idx = row_in_group % len(line_colors)
        color = line_colors[c_idx]
    else:
        # Fallback to matplotlib’s default color cycle
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
    if cal_key:
        lim = calibratables[cal_key]
        if isinstance(lim, dict) and "x" in lim and "y" in lim:
            ax.plot(lim["x"], lim["y"], "r--", label=f"{cal_key}")
        else:
            warnings.warn(f"⚠️ Calibration {cal_limit} found but not in (x,y) format.")
    else:
        warnings.warn(f"⚠️ Calibration limit '{cal_limit}' not found.")