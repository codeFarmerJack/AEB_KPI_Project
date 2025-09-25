import os
import json
import pandas as pd
import matplotlib.pyplot as plt


class ScatterPlotter:
    def __init__(self, graph_spec, line_colors, marker_shapes, calibratables, path_to_csv, path_to_kpi_schema):
        self.graph_spec = graph_spec
        self.line_colors = line_colors.values if isinstance(line_colors, pd.DataFrame) else line_colors
        self.marker_shapes = marker_shapes["Shapes"].tolist() if isinstance(marker_shapes, pd.DataFrame) else marker_shapes
        self.calibratables = calibratables
        self.path_to_csv = path_to_csv
        self.path_to_kpi_schema = path_to_kpi_schema

        # Persistent-like variables
        self.figs = {}
        self.first_rows, self.last_rows, self.title_idx = self._init_group_info(graph_spec)
        self.var_names, self.display_names = self._load_schema_vars(path_to_kpi_schema)

    def plot(self, graph_index: int):
        """Generate scatter plot for one graph index."""

        # Extract x/y vars
        x_var = str(self.graph_spec.loc[0, "Reference"])
        y_var = str(self.graph_spec.loc[graph_index, "Reference"])
        x_label = str(self.graph_spec.loc[0, "Axis_Name"])
        plot_enabled = str(self.graph_spec.loc[graph_index, "plotEnabled"]).strip()

        if plot_enabled.lower() in ["false", "na"]:
            return  # skip

        # Group info
        group_id = self.title_idx[graph_index]
        group_rows = [i for i, g in enumerate(self.title_idx) if g == group_id]
        enabled_rows = [
            r for r in group_rows
            if str(self.graph_spec.loc[r, "plotEnabled"]).lower() not in ["false", "na"]
        ]

        row_in_group = group_rows.index(graph_index)
        first_row, last_row = enabled_rows[0], enabled_rows[-1]

        is_first, is_last = (graph_index == first_row), (graph_index == last_row)

        # Persistent figure
        title_str = str(self.graph_spec.loc[graph_index, "Title"])
        if is_first:
            self.figs[title_str] = self._setup_scatter_figure(
                title_str, first_row, x_label
            )

        fig = self.figs[title_str]
        ax = fig.gca()

        # Process CSVs
        csv_files = [f for f in os.listdir(self.path_to_csv) if f.endswith(".csv")]
        if not csv_files:
            print(f"⚠️ No CSV files found in {self.path_to_csv}")
            return

        for filename in csv_files:
            file_path = os.path.join(self.path_to_csv, filename)
            try:
                data = pd.read_csv(file_path)
            except Exception as e:
                print(f"⚠️ Failed to read {filename}: {e}")
                continue

            x_col, y_col = self._resolve_xy_columns(x_var, y_var, data, filename)
            if x_col is None or y_col is None:
                continue

            filt_idx = self._resolve_filter(plot_enabled, data, filename)
            if filt_idx is None or filt_idx.empty:
                continue

            legend_name = str(self.graph_spec.loc[graph_index, "Legend"])

            x = data.loc[filt_idx, x_col].to_numpy()
            y = data.loc[filt_idx, y_col].to_numpy()

            marker, color = self._select_marker_and_color(group_rows, row_in_group)
            connect_flag = self._resolve_connect_flag(self.graph_spec.loc[graph_index, "ConnectPoints"])

            if connect_flag:
                ax.plot(x, y, linestyle="-", marker=marker, color=color, label=legend_name)
            else:
                ax.plot(x, y, linestyle="none", marker=marker, color=color, label=legend_name)

        # Calibration limits
        cal_limit = str(self.graph_spec.loc[graph_index, "Calibration_Lim"])
        self._add_calibration_limit(cal_limit, ax)

        # Finalize if last in group
        if is_last:
            ax.legend(loc="upper right", fontsize=8)
            ax.grid(True, which="both")
            fig_name = f"Fig_{first_row:02d} - {self.graph_spec.loc[graph_index, 'Legend']}.png"
            out_path = os.path.join(self.path_to_csv, fig_name)
            fig.savefig(out_path, dpi=400)
            print(f"✅ Saved {out_path}")

    # ---------------- Helpers ---------------- #

    def _init_group_info(self, graph_spec):
        unique_titles, title_idx = pd.factorize(graph_spec["Title"])
        group_rows = [list(graph_spec.index[title_idx == g]) for g in range(len(unique_titles))]
        first_rows = [min(g) for g in group_rows]
        last_rows = [max(g) for g in group_rows]
        return first_rows, last_rows, title_idx

    def _load_schema_vars(self, schema_path):
        if not schema_path or not os.path.isfile(schema_path):
            raise FileNotFoundError(f"JSON schema file not found: {schema_path}")

        with open(schema_path, "r") as f:
            schema = json.load(f)

        vars_ = schema["variables"]
        var_names = [v["name"] for v in vars_]
        display_names = [
            f"{v['name']} [{v['unit']}]" if v.get("unit") else v["name"]
            for v in vars_
        ]
        return var_names, display_names

    def _setup_scatter_figure(self, title_str, first_row, x_label):
        fig, ax = plt.subplots(figsize=(9, 6))
        xlim = (self.graph_spec.loc[0, "Min_Axis_value"], self.graph_spec.loc[0, "Max_Axis_value"])
        ylim = (
            self.graph_spec.loc[first_row, "Min_Axis_value"],
            self.graph_spec.loc[first_row, "Max_Axis_value"],
        )
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel(x_label.replace("_", " "))
        ax.set_ylabel(str(self.graph_spec.loc[first_row, "Axis_Name"]).replace("_", " "))
        ax.set_title(title_str)
        return fig

    def _resolve_xy_columns(self, x_var, y_var, data, filename):
        x_candidates = [x_var] + [
            d for v, d in zip(self.var_names, self.display_names) if v.lower() == x_var.lower()
        ]
        y_candidates = [y_var] + [
            d for v, d in zip(self.var_names, self.display_names) if v.lower() == y_var.lower()
        ]
        x_col = next((c for c in x_candidates if c in data.columns), None)
        y_col = next((c for c in y_candidates if c in data.columns), None)
        if not x_col or not y_col:
            print(f"⚠️ X ({x_var}) or Y ({y_var}) not found in {filename}")
        return x_col, y_col

    def _resolve_filter(self, plot_enabled, data, filename):
        if plot_enabled.lower() == "true":
            return data.index
        elif plot_enabled in data.columns:
            col = data[plot_enabled]
            if col.dtype == bool:
                return data.index[col]
            elif col.dtype.kind in "iufc":  # numeric
                return data.index[col != 0]
            elif col.dtype == object or col.dtype.name == "string":
                return data.index[col.astype(str).str.lower() == "true"]
            else:
                print(f"⚠️ Unexpected type in {plot_enabled}, using all rows")
                return data.index
        else:
            print(f"⚠️ Condition {plot_enabled} not found in {filename}, using all rows")
            return data.index

    def _select_marker_and_color(self, group_rows, row_in_group):
        if len(group_rows) == 1:
            return self.marker_shapes[0], self.line_colors[0]
        m_idx = row_in_group % len(self.marker_shapes)
        c_idx = row_in_group % len(self.line_colors)
        return self.marker_shapes[m_idx], self.line_colors[c_idx]

    def _resolve_connect_flag(self, cp_raw):
        if isinstance(cp_raw, (bool, int, float)):
            return bool(cp_raw)
        cp_str = str(cp_raw).strip().lower()
        return cp_str in ["true", "1", "yes", "y"]

    def _add_calibration_limit(self, cal_limit, ax):
        if cal_limit.lower() == "none":
            return
        if cal_limit in self.calibratables:
            lim_data = self.calibratables[cal_limit]
            x, y = lim_data[0], lim_data[1]
            ax.plot(x, y, label=cal_limit)
        else:
            print(f"⚠️ Calibration limit {cal_limit} not found in calibratables")
