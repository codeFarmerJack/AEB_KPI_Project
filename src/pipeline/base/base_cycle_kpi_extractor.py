import os
from abc import ABC, abstractmethod
from src.utils.signal_mdf import safe_load_mdf
from src.utils.create_kpi_table import create_kpi_table_from_df
from src.utils.exporter import export_kpi_to_excel


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
        self.cycle_kpi_table = create_kpi_table_from_df(
            config.cycle_kpi_list,
            feature=self.feature_name
        )

        self.config = config


    # ------------------------------------------------------------------ #
    @abstractmethod
    def extract_cycle_kpis(self, mdf, fname, index):
        """
        Subclass must implement cycle/availability KPI logic.

        Should return a dict:
            { "kpi_name": value, ... }
        """
        pass
    
    # ------------------------------------------------------------------ #
    def export_cycle_kpis(self):
        """Export cycle KPIs into Excel."""

        if self.cycle_kpi_table is None:
            print("ℹ️ No cycle KPI table defined in config.")
            return

        filename = getattr(self.config, "kpi_result_filename", "kpi_results.xlsx")

        # Save under analysis_results
        output_path = os.path.join(self.out_path_results, filename)

        output_path = os.path.abspath(output_path)

        export_kpi_to_excel(
            self.cycle_kpi_table.copy(),
            output_path,
            sheet_name="overall",
        )

        print(f"📄 Exported CYCLE KPIs → sheet 'overall' in {output_path}")

    # ------------------------------------------------------------------ #
    def process_mdf_cycles(self):
        """
        One row per MF4 file.
        Columns come from KPI schema (Common + feature KPIs).
        """

        df_out = self.cycle_kpi_table
        schema = self.config.cycle_kpi_list

        # Pre-extract feature mapping from KPI schema
        feature_lookup = {}
        for _, row in schema.iterrows():
            name = str(row["name"]).strip()
            feat = str(row["feature"]).strip()
            feature_lookup[name] = feat

        for i, fname in enumerate(self.file_list_extracted):
            fpath = os.path.join(self.in_path_extracted, fname)

            # -------------------------
            # Common KPIs
            # -------------------------
            if "label" in df_out.columns:
                df_out.loc[i, "label"] = fname

            if "feature" in df_out.columns:
                # Feature column is per-row, not per-KPI
                df_out.loc[i, "feature"] = self.feature_name

            # -------------------------
            # Load MDF
            # -------------------------
            mdf = safe_load_mdf(fpath)
            if mdf is None:
                continue

            # -------------------------
            # Compute KPIs for this file
            # -------------------------
            result = self.extract_cycle_kpis(mdf, fname, i)
            if not result:
                continue

            # -------------------------
            # Assign KPI values to SAME row
            # -------------------------
            for kpi_name, val in result.items():
                if kpi_name in df_out.columns:
                    df_out.loc[i, kpi_name] = val

        self.cycle_kpi_table = df_out.round(3)
        print(f"\n✅ {self.FEATURE_NAME} Cycle KPI extraction completed successfully.")

