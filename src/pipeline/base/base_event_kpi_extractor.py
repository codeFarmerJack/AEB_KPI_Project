import os
import warnings
import numpy as np
from src.utils.signal_mdf import SignalMDF
from src.utils.create_kpi_table import create_kpi_table_from_df
from src.utils.exporter import export_kpi_to_excel


class BaseEventKpiExtractor:
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
        Export KPI results to Excel using the shared helper (export_kpi_to_excel).
        - Always export `kpi_table` as one sheet.
        - Export `overall_kpi_table` as an additional sheet (if it exists).
        - Ensures consistent sheet naming and correct Excel file naming.
        """

        # ------------------------------------------------------------
        # 1. Determine sheet name (normalize to lowercase)
        # ------------------------------------------------------------
        event_sheet = (sheet_name or self.feature_name).lower()

        # ------------------------------------------------------------
        # 2. Determine FINAL Excel file output path
        # ------------------------------------------------------------
        # Use config if provided, else fallback
        filename = getattr(self.config, "kpi_result_filename", "kpi_results.xlsx")

        # Full path: <results_folder>/<filename>
        output_path = os.path.join(self.out_path_results, filename)

        try:
            # =====================================================
            # 1) MAIN KPI TABLE — always exported
            # =====================================================
            df_main = self.kpi_table.copy()

            # Sort BEFORE renaming
            if "vehSpd" in df_main.columns:
                df_main = df_main.sort_values("vehSpd")
            else:
                print("⚠️ 'vehSpd' not found in main KPI table — skipping sort.")

            # Write/append sheet using helper
            export_kpi_to_excel(df_main, output_path, sheet_name=event_sheet)
            print(f"📄 Exported '{event_sheet}' sheet → {output_path}")

            # =====================================================
            # 2) OVERALL TABLE — only exported when available
            # =====================================================
            if self.overall_kpi_table is not None and not self.overall_kpi_table.empty:
                df_overall = self.overall_kpi_table.copy()

                export_kpi_to_excel(df_overall, output_path, sheet_name="overall")
                print("📄 Exported 'overall' KPI sheet.")
            else:
                print("ℹ️ No overall KPI table — only main sheet exported.")

            print(f"✅ KPI export completed successfully → {output_path}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export KPI results to Excel ({output_path}): {e}")

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process_all_mdf_files()")
