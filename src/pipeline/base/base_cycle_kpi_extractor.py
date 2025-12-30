from abc import ABC, abstractmethod
import os
import warnings

import pandas as pd

from src.utils.signal_mdf import safe_load_mdf
from src.utils.create_kpi_table import create_kpi_table_from_df
from src.utils.exporter import export_kpi_to_excel
from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer


class BaseCycleKpiExtractor(ABC):
    """
    Base class for cycle/availability KPIs (file-level summaries).

    Criteria and flow:
    - Operates on full extracted MF4 logs (not event chunks).
    - Produces ONE ROW per (file x feature) with distance-weighted KPIs.
    - Subclasses decide KPI criteria and should return:
      { "<FEATURE>": {"kpi_name": value, ...}, ... }
    """

    FEATURE_NAME = "BASE_CYCLE"
    _CYCLE_SHEET_NAME = "cycleKPI"
    _SCHEMA_REQUIRED_COLS = ("feature", "name")

    def __init__(self, input_handler, config):
        self._validate_inputs(input_handler, config)
        self.config = config
        self.feature_name = self.FEATURE_NAME
        self._init_paths(input_handler)
        self.file_list_extracted = self._collect_extracted_files(self.in_path_extracted)
        self._init_cycle_schema(config)


    # ------------------------------------------------------------------ #
    @abstractmethod
    def extract_cycle_kpis(self, mdf, fname):
        """
        Subclass must implement cycle/availability KPI logic and criteria.

        Expected return structure:
        { "<FEATURE>": {"kpi_name": value, ...}, ... }
        """
        pass
    
    # ------------------------------------------------------------------ #
    def export_cycle_kpis(self):
        """Export cycle KPIs into Excel."""

        if self._cycle_table_empty():
            print("ℹ️ No cycle KPIs to export; skipping cycleKPI sheet.")
            return

        output_path = self._cycle_output_path()
        df_out = self.cycle_kpi_table.copy()
        df_out = self._merge_existing_cycle_sheet(df_out, output_path)
        df_out.attrs["display_names"] = self._get_schema_display_map()
        export_kpi_to_excel(df_out, output_path, sheet_name=self._CYCLE_SHEET_NAME)

        print(f"📄 Exported CYCLE KPIs → sheet 'cycleKPI' in {output_path}")

    # ------------------------------------------------------------------ #
    def process_mdf_cycles(self):
        """
        For cycle KPIs, produce ONE ROW PER (file × feature).
        Example:
            file1 - AEB
            file1 - FCW
            file1 - EBA
        """

        if self.cycle_kpi_table is None:
            warnings.warn("⚠️ cycle_kpi_table not initialized; skipping cycle KPI processing.")
            return

        rows = self._collect_cycle_rows()
        self._build_cycle_table(rows)
        self._finalize_cycle_table()

    # ------------------------------------------------------------------ #
    def get_feature_kpi_names(self, feature_name: str):
        """
        Return the list of KPI 'name' entries defined for a feature in the cycle schema.
        """
        if not self._schema_has_columns(*self._SCHEMA_REQUIRED_COLS):
            return []

        feat = self._normalize_key(feature_name)
        names = self.cycle_kpi_schema.loc[
            self.cycle_kpi_schema["feature"].astype(str).str.strip().str.lower() == feat,
            "name",
        ]
        return [str(n) for n in names.dropna().tolist()]

    # ------------------------------------------------------------------ #
    def render_cycle_dashboards(self, feature_name: str):
        """
        Generate per-file cycle dashboards using CycleVisualizer.
        """
        if self._cycle_table_empty():
            return

        out_dir = self._cycle_out_dir(feature_name)
        viz = BaseCycleVisualizer(out_dir)

        viz.render_dashboards(
            self.cycle_kpi_table,
            feature_name,
            self.in_path_extracted,
        )

    def _get_schema_display_map(self):
        if self.cycle_kpi_schema is None:
            return {}
        schema_base = create_kpi_table_from_df(
            self.cycle_kpi_schema,
            feature=self.feature_name
        )
        return schema_base.attrs.get("display_names", {})

    def _validate_inputs(self, input_handler, config):
        if input_handler is None or config is None:
            raise ValueError("Both InputHandler and Config are required.")

    def _init_paths(self, input_handler):
        self.in_path_raw_data = input_handler.in_path_raw_data
        self.out_path_results = os.path.join(self.in_path_raw_data, "analysis_results")
        os.makedirs(self.out_path_results, exist_ok=True)
        self.in_path_extracted = input_handler.out_path_extracted

    def _collect_extracted_files(self, path):
        files = [f for f in os.listdir(path) if f.lower().endswith(".mf4")]
        if not files:
            raise FileNotFoundError(f"No extracted .mf4 files found in {path}")
        return files

    def _init_cycle_schema(self, config):
        schema_df = getattr(config, "cycle_kpi_list", None)
        if not isinstance(schema_df, pd.DataFrame) or schema_df.empty:
            warnings.warn("⚠️ cycle_kpi_list is missing or empty; skipping cycle KPI extraction.")
            self.cycle_kpi_table = pd.DataFrame(columns=["label", "feature"])
            self.cycle_kpi_schema = None
            self.cycle_display_map = {}
            return

        schema_df = schema_df.copy()
        schema_df.columns = schema_df.columns.str.strip().str.lower()
        self.cycle_kpi_schema = schema_df
        self.cycle_kpi_table = create_kpi_table_from_df(self.cycle_kpi_schema, feature=self.feature_name)
        self.cycle_display_map = self.cycle_kpi_table.attrs.get("display_names", {})

    def _cycle_table_empty(self):
        return self.cycle_kpi_table is None or self.cycle_kpi_table.empty

    def _cycle_output_path(self):
        filename = getattr(self.config, "kpi_result_filename", "kpi_results.xlsx")
        output_path = os.path.join(self.out_path_results, filename)
        return os.path.abspath(output_path)

    def _cycle_out_dir(self, feature_name):
        return os.path.join(self.out_path_results, feature_name.lower(), "cycle")

    def _merge_existing_cycle_sheet(self, df_out, output_path):
        if not os.path.exists(output_path):
            return df_out

        try:
            prev = pd.read_excel(output_path, sheet_name=self._CYCLE_SHEET_NAME)
            inv_display_map = self._invert_display_map(self._get_schema_display_map())
            prev = prev.rename(columns=lambda c: inv_display_map.get(c, c))
            df_out = (
                pd.concat([prev, df_out], ignore_index=True, sort=False)
                .drop_duplicates(subset=["label", "feature"], keep="last")
                .reset_index(drop=True)
            )
            print(f"🔁 Merged existing cycleKPI sheet with {len(self.cycle_kpi_table)} new rows.")
        except Exception as e:
            warnings.warn(f"⚠️ Could not merge existing cycleKPI sheet; writing new one. Details: {e}")
        return df_out

    def _invert_display_map(self, display_map):
        return {v: k for k, v in (display_map or {}).items()}

    def _collect_cycle_rows(self):
        rows = []
        for fname in self.file_list_extracted:
            rows.extend(self._process_cycle_file(fname))
        return rows

    def _process_cycle_file(self, fname):
        fpath = os.path.join(self.in_path_extracted, fname)
        mdf = safe_load_mdf(fpath)
        if mdf is None:
            return []

        feature_results = self.extract_cycle_kpis(mdf, fname)
        if not feature_results:
            return []

        return [
            self._build_cycle_row(fname, feature_name, kpi_dict)
            for feature_name, kpi_dict in feature_results.items()
        ]

    def _build_cycle_row(self, fname, feature_name, kpi_dict):
        row = {
            "label": fname,
            "feature": feature_name,
        }
        row.update(kpi_dict)
        return row

    def _build_cycle_table(self, rows):
        display_map = self._get_schema_display_map()
        new_df = pd.DataFrame(rows)
        desired_cols = self._desired_cycle_columns(new_df)
        self.cycle_kpi_table = new_df.reindex(columns=desired_cols, fill_value=None).round(3)
        self.cycle_display_map = self._build_cycle_display_map(display_map, self.cycle_kpi_table.columns)
        self.cycle_kpi_table.attrs["display_names"] = self.cycle_display_map

    def _desired_cycle_columns(self, new_df):
        base_cols = ["label", "feature"]
        return base_cols + [c for c in new_df.columns if c not in base_cols]

    def _build_cycle_display_map(self, display_map, columns):
        safe_map = dict(display_map) if display_map else {}
        for col in columns:
            if col not in safe_map:
                safe_map[col] = col
        return safe_map

    def _finalize_cycle_table(self):
        if self.cycle_kpi_table.empty:
            warnings.warn("⚠️ No cycle KPIs produced; cycleKPI sheet will not be written.")
        else:
            print(f"🧾 Collected {len(self.cycle_kpi_table)} cycle KPI rows.")

        print(f"\n✅ {self.FEATURE_NAME} Cycle KPI extraction completed successfully.")

    def _schema_has_columns(self, *cols):
        if self.cycle_kpi_schema is None:
            return False
        return all(col in self.cycle_kpi_schema.columns for col in cols)

    def _normalize_key(self, value):
        return str(value).strip().lower()
