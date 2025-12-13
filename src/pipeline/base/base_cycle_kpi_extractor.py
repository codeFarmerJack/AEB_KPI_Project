import os
import warnings
from pathlib import Path
import pandas as pd
from abc import ABC, abstractmethod
from src.utils.signal_mdf import safe_load_mdf, get_signal
from src.utils.create_kpi_table import create_kpi_table_from_df
from src.utils.exporter import export_kpi_to_excel
from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer


class BaseCycleKpiExtractor(ABC):
    """
    Base class for CYCLE / AVAILABILITY KPIs.
    - Operates on extracted MF4 logs
    - Maintains its own file_list_extracted
    - Owns overall_kpi_table
    """

    FEATURE_NAME = "BASE_CYCLE"

    def __init__(self, input_handler, config):
        if input_handler is None or config is None:
            raise ValueError("Both InputHandler and Config are required.")

        # Paths
        self.in_path_raw_data  = input_handler.in_path_raw_data
        self.out_path_results  = os.path.join(self.in_path_raw_data, "analysis_results")
        os.makedirs(self.out_path_results, exist_ok=True)

        self.in_path_extracted = input_handler.out_path_extracted

        # Extracted MF4 logs
        self.file_list_extracted = [
            f for f in os.listdir(self.in_path_extracted)
            if f.lower().endswith(".mf4")
        ]
        if not self.file_list_extracted:
            raise FileNotFoundError(f"No extracted .mf4 files found in {self.in_path_extracted}")

        # Cycle KPI table (from config.cycle_kpi_list)
        self.feature_name = self.FEATURE_NAME
        schema_df = getattr(config, "cycle_kpi_list", None)
        if not isinstance(schema_df, pd.DataFrame) or schema_df.empty:
            warnings.warn("⚠️ cycle_kpi_list is missing or empty; skipping cycle KPI extraction.")
            self.cycle_kpi_table = pd.DataFrame(columns=["label", "feature"])
            self.cycle_kpi_schema = None
            self.cycle_display_map = {}
        else:
            schema_df = schema_df.copy()
            schema_df.columns = schema_df.columns.str.strip().str.lower()
            self.cycle_kpi_schema = schema_df
            self.cycle_kpi_table = create_kpi_table_from_df(self.cycle_kpi_schema, feature=self.feature_name)
            self.cycle_display_map = self.cycle_kpi_table.attrs.get("display_names", {})

        self.config = config


    # ------------------------------------------------------------------ #
    @abstractmethod
    def extract_cycle_kpis(self, mdf, fname):
        """
        Subclass must implement cycle/availability KPI logic.

        Should return a dict:
            { "kpi_name": value, ... }
        """
        pass
    
    # ------------------------------------------------------------------ #
    def export_cycle_kpis(self):
        """Export cycle KPIs into Excel."""

        if self.cycle_kpi_table is None or self.cycle_kpi_table.empty:
            print("ℹ️ No cycle KPIs to export; skipping cycleKPI sheet.")
            return

        filename = getattr(self.config, "kpi_result_filename", "kpi_results.xlsx")

        # Save under analysis_results
        output_path = os.path.join(self.out_path_results, filename)

        output_path = os.path.abspath(output_path)

        df_out = self.cycle_kpi_table.copy()

        # Merge with existing cycleKPI sheet so multiple features coexist
        if os.path.exists(output_path):
            try:
                # --- load previous Excel sheet ---
                prev = pd.read_excel(output_path, sheet_name="cycleKPI")

                # --- build inverse display map from schema (authoritative) ---
                display_map = self._get_schema_display_map()

                inv_display_map = {v: k for k, v in display_map.items()}

                # --- normalize Excel headers back to internal keys ---
                prev = prev.rename(columns=lambda c: inv_display_map.get(c, c))
                
                # --- concatenate and drop duplicates (keep latest) ---
                df_out = (
                    pd.concat([prev, df_out], ignore_index=True, sort=False)
                    .drop_duplicates(subset=["label", "feature"], keep="last")
                    .reset_index(drop=True)
                )
                print(f"🔁 Merged existing cycleKPI sheet with {len(self.cycle_kpi_table)} new rows.")
            except Exception as e:
                warnings.warn(f"⚠️ Could not merge existing cycleKPI sheet; writing new one. Details: {e}")

        # Re-attach canonical display names (with units) before export
        df_out.attrs["display_names"] = self._get_schema_display_map()

        export_kpi_to_excel(df_out, output_path, sheet_name="cycleKPI",)

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

        rows = []  # collect rows for final DataFrame

        for fname in self.file_list_extracted:
            fpath = os.path.join(self.in_path_extracted, fname)

            # Load MDF
            mdf = safe_load_mdf(fpath)
            if mdf is None:
                continue

            # Compute KPIs for ALL features in this file
            # Should return:
            # {
            #   "AEB": {"AvailDistPctLeft": 67.3, "AvailDistPctRight": 67.3},
            #   "FCW": {...},
            #   "EBA": {...},
            # }
            feature_results = self.extract_cycle_kpis(mdf, fname)

            if not feature_results:
                continue

            # Append one row per feature
            for feature_name, kpi_dict in feature_results.items():
                row = {
                    "label": fname,
                    "feature": feature_name,
                }
                row.update(kpi_dict)  # add KPI columns
                rows.append(row)

        # Convert collected rows to DataFrame and preserve any KPI keys
        # Always load the canonical display map from schema
        display_map = self._get_schema_display_map()
        new_df = pd.DataFrame(rows)

        # Build desired columns: keep label/feature + keys present in data
        desired_cols = ["label", "feature"]
        desired_cols += [c for c in new_df.columns if c not in desired_cols]

        self.cycle_kpi_table = new_df.reindex(columns=desired_cols, fill_value=None).round(3)

        # restore display map so exporter can rename columns
        if not display_map:
            display_map = {}
        # Only add names that do NOT exist in schema
        safe_map = dict(display_map)  # make a copy to avoid aliasing

        for col in self.cycle_kpi_table.columns:
            if col not in safe_map:
                safe_map[col] = col   # add new names, DO NOT overwrite existing schema-based ones
        
        # store final mapping 
        self.cycle_display_map = safe_map
        self.cycle_kpi_table.attrs["display_names"] = safe_map

        if self.cycle_kpi_table.empty:
            warnings.warn("⚠️ No cycle KPIs produced; cycleKPI sheet will not be written.")
        else:
            print(f"🧾 Collected {len(self.cycle_kpi_table)} cycle KPI rows.")

        print(f"\n✅ {self.FEATURE_NAME} Cycle KPI extraction completed successfully.")

    # ------------------------------------------------------------------ #
    def get_feature_kpi_names(self, feature_name: str):
        """
        Return the list of KPI 'name' entries defined for a feature in the cycle schema.
        """
        if self.cycle_kpi_schema is None:
            return []
        if "feature" not in self.cycle_kpi_schema.columns or "name" not in self.cycle_kpi_schema.columns:
            return []

        feat = str(feature_name).strip().lower()
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
        if self.cycle_kpi_table is None or self.cycle_kpi_table.empty:
            return

        out_dir = os.path.join(self.out_path_results, feature_name.lower(), "cycle")
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
