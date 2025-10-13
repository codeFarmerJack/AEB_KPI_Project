import os
import warnings
import numpy as np
import pandas as pd

# --- Local utils imports ---
from utils.signal_mdf import SignalMDF
from utils.create_kpi_table import create_kpi_table_from_df
from utils.data_utils import safe_scalar
from utils.exporter import export_kpi_to_excel

# Import all FCW KPI functions (via __init__.py)
from utils.kpis.fcw import *


# ------------------------------------------------------------------ #
# FCW KPI Extractor
# ------------------------------------------------------------------ #
class FcwKpiExtractor:
    """Extracts FCW KPI metrics from MF4 chunks."""

    # --- Fallback defaults ---
    WINDOW_S     = 1.0   # seconds for jerk calculation window
    JERK_THD     = 5.0   # m/s³ threshold for brake jerk detection

    def __init__(self, config, event_detector):
        if config is None or event_detector is None:
            raise ValueError("Config and FcwEventSegmenter are required.")
        if not hasattr(event_detector, "path_to_fcw_chunks"):
            raise TypeError("event_detector must have path_to_fcw_chunks attribute.")

        # --- Setup paths ---
        self.path_to_mdf     = event_detector.path_to_mdf
        self.path_to_results = os.path.join(self.path_to_mdf, "analysis_results")

        if not os.path.exists(self.path_to_results):
            os.makedirs(self.path_to_results)

        self.path_to_chunks  = event_detector.path_to_fcw_chunks
        self.file_list       = [f for f in os.listdir(self.path_to_chunks) if f.endswith(".mf4")]

        if not self.file_list:
            raise FileNotFoundError(f"No .mf4 files in {self.path_to_chunks}")

        # --- KPI table creation ---
        self.kpi_table = create_kpi_table_from_df(config.kpi_spec, feature="FCW")

        # --- Initialize default parameters ---
        self._apply_defaults()

        # --- Apply overrides from Config.params (if present) ---
        if hasattr(config, "params") and isinstance(config.params, dict):
            params = config.params
            print("⚙️ Applying parameter overrides from config.params")

            self.window_s     = float(params.get("WINDOW_S", self.window_s))
            self.jerk_thd     = float(params.get("JERK_THD", self.jerk_thd))

        # --- Debug summary ---
        print(
            f"\n📊 FCW KPI Parameter Summary:\n"
            f"   WINDOW_S     = {self.window_s}\n"
            f"   JERK_THD     = {self.jerk_thd}\n"
        )

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all .mf4 chunk files and calculate KPIs."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_chunks, fname)
            print(f"🔍 Processing {fname}")

            # --- Prepare label column ---
            if "label" not in self.kpi_table.columns:
                self.kpi_table.insert(0, "label", "")
            self.kpi_table.loc[i, "label"] = fname

            try:
                mdf = SignalMDF(fpath)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to read {fname}: {e}")
                continue

            # --- Extract key signals ---
            time          = mdf.time
            ego_speed     = mdf.egoSpeedKph
            fcw_request   = mdf.fcwRequest
            accel         = mdf.longAccelFilt

            if accel is None or fcw_request is None:
                warnings.warn(f"⚠️ Missing accel or fcwRequest in {fname} → skipped.")
                continue

            # --- FCW event detection ---
            brake_jerk(mdf, self.kpi_table, i, window_s=self.window_s, jerk_thresh=self.jerk_thd)

            # --- Save core timings ---
            self.kpi_table.loc[i, "logTime"]         = safe_scalar(fcw_start_time)

            if np.isfinite(safe_scalar(fcw_start_time)) and np.isfinite(safe_scalar(fcw_end_time)):
                self.kpi_table.loc[i, "fcwDur"] = round(
                    float(fcw_end_time) - float(fcw_start_time), 2
                )

            # --- Vehicle speed at start ---
            veh_spd = np.nan
            if fcw_start_idx is not None and fcw_start_idx < len(ego_speed):
                veh_spd = safe_scalar(ego_speed[fcw_start_idx])
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- KPI metric calculations ---
            # (Each subfunction updates kpi_table in place)
            brake_jerk(mdf, self.kpi_table, i, fcw_start_idx)
            # Add other FCW KPIs here (placeholders)
            # e.g. peakDecel(), peakJerk(), fcw_latency()

            # Round final KPI table for export
            self.kpi_table = self.kpi_table.round(3)

    # ------------------------------------------------------------------ #
    def export_to_excel(self):
        """Export FCW KPI results to Excel (sheet: 'fcw')."""
        try:
            export_kpi_to_excel(self.kpi_table, self.path_to_results, sheet_name="fcw")
        except Exception as e:
            warnings.warn(f"⚠️ Failed to export FCW KPI results: {e}")

# ------------------------------------------------------------------ #
    def _apply_defaults(self):
        """Apply default parameter values."""
        self.window_s    = self.WINDOW_S
        self.jerk_thd    = self.JERK_THD

        print(
            f"⚙️ Using default parameters: "
            f"WINDOW_S={self.window_s}, JERK_THD={self.jerk_thd}, "
        )
