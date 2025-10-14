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
    def __init__(self, config, event_detector, chunk_attr_name, feature_name=None):
        if config is None or event_detector is None:
            raise ValueError("Both Config and EventDetector are required.")

        if not hasattr(event_detector, chunk_attr_name):
            raise TypeError(f"event_detector missing required attribute '{chunk_attr_name}'")

        # --- Setup paths ---
        self.path_to_mdf = event_detector.path_to_mdf
        self.path_to_results = os.path.join(self.path_to_mdf, "analysis_results")
        os.makedirs(self.path_to_results, exist_ok=True)

        self.path_to_chunks = getattr(event_detector, chunk_attr_name)
        self.file_list = [f for f in os.listdir(self.path_to_chunks) if f.endswith(".mf4")]
        if not self.file_list:
            raise FileNotFoundError(f"No .mf4 files found in {self.path_to_chunks}")

        # --- KPI table ---
        self.feature_name = feature_name or self.FEATURE_NAME
        self.kpi_table = create_kpi_table_from_df(config.kpi_spec, feature=self.feature_name)

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
        """Export KPI results to Excel."""
        sheet = sheet_name or self.feature_name.lower()
        try:
            export_kpi_to_excel(self.kpi_table, self.path_to_results, sheet_name=sheet)
        except Exception as e:
            warnings.warn(f"⚠️ Failed to export KPI results for {sheet}: {e}")

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement process_all_mdf_files()")
