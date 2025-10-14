import os
import warnings
import numpy as np
import pandas as pd

# --- Local utils imports ---
from utils.signal_mdf import SignalMDF
from utils.create_kpi_table import create_kpi_table_from_df
from utils.data_utils import safe_scalar
from utils.load_params import load_params_from_class, load_params_from_config
from utils.exporter import export_kpi_to_excel
from utils.event_detector.fcw import detect_fcw_events

# Import all FCW KPI functions (via __init__.py)
from utils.kpis.fcw import *


# ------------------------------------------------------------------ #
# FCW KPI Extractor
# ------------------------------------------------------------------ #
class FcwKpiExtractor:
    """Extracts FCW KPI metrics from MF4 chunks."""

    # --- Default fallback parameters ---
    WINDOW_S             = 1.0     # seconds for jerk calculation window
    JERK_NEG_THD         = -20.0   # m/s³ threshold for negative jerk
    JERK_POS_THD         = 20.0    # m/s³ threshold for positive jerk
    BRAKEJERK_MIN_SPEED  = 30.0    # minimum valid vehicle speed (kph)
    BRAKEJERK_MAX_SPEED  = 130.0   # maximum valid vehicle speed (kph)

    def __init__(self, config, event_detector):
        if config is None or event_detector is None:
            raise ValueError("Config and EventDetector are required.")
        if not hasattr(event_detector, "path_to_fcw_chunks"):
            raise TypeError("event_detector must have path_to_fcw_chunks attribute.")

        # --- Setup paths ---
        self.path_to_mdf     = event_detector.path_to_mdf
        self.path_to_results = os.path.join(self.path_to_mdf, "analysis_results")
        os.makedirs(self.path_to_results, exist_ok=True)

        self.path_to_chunks  = event_detector.path_to_fcw_chunks
        self.file_list       = [f for f in os.listdir(self.path_to_chunks) if f.endswith(".mf4")]
        if not self.file_list:
            raise FileNotFoundError(f"No .mf4 files found in {self.path_to_chunks}")

        # --- Create KPI table ---
        self.kpi_table = create_kpi_table_from_df(config.kpi_spec, feature="FCW")
        
        # --- Load parameters from class and config using mapping ---
        mapping = {
            "JERK_NEG_THD": "jerk_neg_thd",
            "JERK_POS_THD": "jerk_pos_thd",
            "WINDOW_S": "window_s",
            "BRAKEJERK_MIN_SPEED": "brakejerk_min_speed",
            "BRAKEJERK_MAX_SPEED": "brakejerk_max_speed",
        }
        # --- Load defaults then overrides ---
        load_params_from_class(self, mapping)
        load_params_from_config(self, config, mapping)

        # --- Debug summary ---
        print(
            f"\n📊 FCW KPI Parameter Summary:\n"
            f"   WINDOW_S             = {self.window_s}\n"
            f"   JERK_NEG_THD         = {self.jerk_neg_thd}\n"
            f"   JERK_POS_THD         = {self.jerk_pos_thd}\n"
            f"   BRAKEJERK_MIN_SPEED  = {self.brakejerk_min_speed}\n"
            f"   BRAKEJERK_MAX_SPEED  = {self.brakejerk_max_speed}\n"
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

            # --- Load MDF file ---
            try:
                mdf = SignalMDF(fpath)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to read {fname}: {e}")
                continue

            # --- Extract signals ---
            time        = mdf.time
            accel       = mdf.longActAccelFlt
            fcw_request = mdf.fcwRequest
            ego_speed   = mdf.egoSpeedKph

            if accel is None or fcw_request is None:
                warnings.warn(f"⚠️ Missing accel or fcwRequest in {fname} → skipped.")
                continue

            # --- FCW event detection ---
            start_times, end_times = detect_fcw_events(time, fcw_request)
            if len(start_times) == 0:
                print(f"⚠️ No FCW events detected in {fname}")
                continue

            # --- Use first FCW event ---
            fcw_start_time = start_times[0]
            fcw_end_time   = end_times[0] if len(end_times) > 0 else np.nan
            self.kpi_table.loc[i, "logTime"] = safe_scalar(fcw_start_time)

            # --- Vehicle speed at FCW start ---
            fcw_start_idx = int(np.argmin(np.abs(time - fcw_start_time)))
            veh_spd = np.nan
            if ego_speed is not None and fcw_start_idx < len(ego_speed):
                veh_spd = safe_scalar(ego_speed[fcw_start_idx])
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- KPI metric calculations ---
            brake_jerk(self, mdf, i)

            self.kpi_table = self.kpi_table.round(3)

    # ------------------------------------------------------------------ #
    def export_to_excel(self):
        """Export FCW KPI results to Excel (sheet: 'fcw')."""
        try:
            export_kpi_to_excel(self.kpi_table, self.path_to_results, sheet_name="fcw")
        except Exception as e:
            warnings.warn(f"⚠️ Failed to export FCW KPI results: {e}")
