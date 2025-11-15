import os
import warnings
import numpy as np
import pandas as pd
from utils.signal_mdf import SignalMDF
from utils.create_kpi_table import create_kpi_table_from_df
from utils.exporter import export_kpi_to_excel
from utils.data_utils import safe_scalar


class BaseKpiExtractor:
    """
    Base class for KPI extractors (AEB, FCW, etc.)
    Handles shared setup, parameter loading, and export logic.
    Subclasses must define:
        - FEATURE_NAME
        - PARAM_SPECS
        - process_all_mdf_files()
    """

    FEATURE_NAME = "BASE"
    PARAM_SPECS = {}

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter, chunk_attr_name, feature_name=None):
        if config is None or event_segmenter is None:
            raise ValueError("Both Config and EventSegmenter are required.")

        if not hasattr(event_segmenter, chunk_attr_name):
            raise TypeError(f"event_segmenter missing required attribute '{chunk_attr_name}'")

        # --- Setup paths ---
        self.in_path_raw_data  = event_segmenter.in_path_raw_data
        self.out_path_results  = os.path.join(self.in_path_raw_data, "analysis_results")
        os.makedirs(self.out_path_results, exist_ok=True)

        self.in_path_extracted = event_segmenter.in_path_extracted
        self.out_path_chunks = getattr(event_segmenter, chunk_attr_name)

        # ---- Chunked MF4 files (for event-based KPI extraction)
        self.file_list = [f for f in os.listdir(self.out_path_chunks) if f.endswith(".mf4")]
        if not self.file_list:
            raise FileNotFoundError(f"No .mf4 files found in {self.out_path_chunks}")

        # ---- Extracted MF4 files (for availability KPI extraction)
        self.file_list_extracted = [
            f for f in os.listdir(self.in_path_extracted) if f.endswith(".mf4")
        ]
        if not self.file_list_extracted:
            raise FileNotFoundError(f"No .mf4 extracted files found in {self.in_path_extracted}")

        # --- KPI table ---
        self.feature_name = feature_name or self.FEATURE_NAME
        self.kpi_table = create_kpi_table_from_df(config.kpi_spec, feature=self.feature_name)

        # ---------------------------------------------------------
        # OPTIONAL: Create overall_kpi_table if config.overall_kpi exists
        # ---------------------------------------------------------
        if hasattr(config, "overall_kpi") and config.overall_kpi is not None:
            self.overall_kpi_table = create_kpi_table_from_df(
                config.overall_kpi,
                feature=self.feature_name
            )
        else:
            self.overall_kpi_table = None

        # --- Parameter loading ---
        self._load_params(config)

        # --- Store config for later use ---
        self.config = config

    # ------------------------------------------------------------------ #
    def _load_params(self, config):
        """Load default parameters and apply overrides from config.params."""
        cls_name = self.__class__.__name__
        print(f"\n⚙️ Loading parameters for {cls_name}...")

        # 1️⃣ Load defaults from PARAM_SPECS
        for name, spec in self.PARAM_SPECS.items():
            default_val = spec.get("default")
            setattr(self, name, default_val)
            print(f"   • {name:<18} ← {default_val} (default)")

        # 2️⃣ Apply overrides from config.params (if available)
        params = getattr(config, "params", {})
        for name, spec in self.PARAM_SPECS.items():
            # try both param name and param_name_<feature>
            keys = [name, f"{name}_{self.feature_name.lower()}"]
            for key in keys:
                if key in params:
                    try:
                        val = spec.get("type", float)(params[key])
                        setattr(self, name, val)
                        print(f"   ✅ {name:<18} overridden ← {val} (from '{key}')")
                        break
                    except Exception as e:
                        warnings.warn(f"⚠️ Could not parse {key}: {e}")

    # ------------------------------------------------------------------ #
    def _load_mdf(self, fpath):
        """Load MDF file safely."""
        try:
            return SignalMDF(fpath)
        except Exception as e:
            warnings.warn(f"⚠️ Failed to read {os.path.basename(fpath)}: {e}")
            return None

    def _prepare_time(self, mdf):
        """Extract or synthesize a time vector."""
        time = getattr(mdf, "time", None)
        if time is None or len(time) == 0:
            try:
                time = mdf.get_master(0).flatten()
            except Exception:
                n = len(mdf.groups[0].channels[0].samples) if mdf.groups else 0
                time = np.arange(n, dtype=float)
            warnings.warn("⚠️ Synthesized time vector (equidistant).")
        return time

    def _insert_label(self, index, fname):
        """Ensure label column exists and assign filename."""
        if "label" not in self.kpi_table.columns:
            self.kpi_table.insert(0, "label", "")
        self.kpi_table.loc[index, "label"] = fname

    # ------------------------------------------------------------------ #
    def export_to_excel(self, sheet_name=None):
        """
        Export KPI results to Excel.
        - If overall_kpi_table exists and is not empty → export two sheets.
        - Otherwise → export only kpi_table.
        """

        # Determine sheet names
        event_sheet   = sheet_name or self.feature_name.lower()
        overall_sheet = "overall"

        # Output file
        filename = getattr(self.config, "kpi_result_filename", "kpi_results.xlsx")
        output_path = os.path.join(self.out_path_results, filename)

        # Helper: apply display names (units etc.)
        def apply_display_names(df):
            if hasattr(df, "attrs") and "display_names" in df.attrs:
                return df.rename(columns=df.attrs["display_names"])
            return df

        try:
            # ----------------------------
            # CASE 1: No overall KPI table
            # ----------------------------
            if self.overall_kpi_table is None or self.overall_kpi_table.empty:
                df_main = apply_display_names(self.kpi_table)

                export_kpi_to_excel(df_main, output_path, sheet_name=event_sheet)
                print(f"💾 Saved KPI results → {output_path} (single sheet)")
                return

            # ----------------------------
            # CASE 2: Export two sheets
            # ----------------------------
            df_main   = apply_display_names(self.kpi_table)
            df_over   = apply_display_names(self.overall_kpi_table)

            with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                df_main.to_excel(writer,   index=False, sheet_name=event_sheet)
                df_over.to_excel(writer,   index=False, sheet_name=overall_sheet)

            print(f"💾 Saved KPI results → {output_path} (two sheets)")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export KPI results: {e}")


    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process_all_mdf_files()")
