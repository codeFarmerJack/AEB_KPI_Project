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
        For cycle KPIs, produce ONE ROW PER (file × feature).
        Example:
            file1 - AEB
            file1 - FCW
            file1 - EBA
        """

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

        # Convert collected rows to DataFrame
        self.cycle_kpi_table = (
            pd.DataFrame(rows)
            .reindex(columns=self.cycle_kpi_table.columns, fill_value=None)
            .round(3)
        )

        print(f"\n✅ {self.FEATURE_NAME} Cycle KPI extraction completed successfully.")


