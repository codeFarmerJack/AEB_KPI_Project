import os
import numpy as np
import warnings
from pipeline.base.base_kpi_extractor import BaseKpiExtractor
from utils.event_detector.fcw import detect_fcw_events
from utils.data_utils import safe_scalar
from utils.kpis.fcw import *


# ------------------------------------------------------------------ #
# FCW KPI Extractor
# ------------------------------------------------------------------ #
class FcwKpiExtractor(BaseKpiExtractor):
    """Extracts FCW KPI metrics from MF4 chunks."""

    FEATURE_NAME = "FCW"
    PARAM_SPECS = {
        "window_s":            {"default": 1.0,   "type": float, "desc": "Sliding window duration (s)"},
        "jerk_neg_thd":        {"default": -20.0, "type": float, "desc": "Negative jerk threshold (m/s³)"},
        "jerk_pos_thd":        {"default": 20.0,  "type": float, "desc": "Positive jerk threshold (m/s³)"},
        "brakejerk_min_speed": {"default": 30.0,  "type": float, "desc": "Minimum valid speed (kph)"},
        "brakejerk_max_speed": {"default": 130.0, "type": float, "desc": "Maximum valid speed (kph)"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_detector):
        super().__init__(config, event_detector, "path_to_fcw_chunks", feature_name="FCW")

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all FCW MF4 chunk files and calculate KPIs."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_chunks, fname)
            self._insert_label(i, fname)

            mdf = self._load_mdf(fpath)
            if mdf is None:
                continue

            # --- Extract signals ---
            time        = self._prepare_time(mdf)
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

            fcw_start_time = start_times[0]
            self.kpi_table.loc[i, "logTime"] = safe_scalar(fcw_start_time)

            # --- Vehicle speed at FCW start ---
            fcw_start_idx = int(np.argmin(np.abs(time - fcw_start_time)))
            veh_spd = safe_scalar(ego_speed[fcw_start_idx]) if ego_speed is not None else np.nan
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- KPI metrics ---
            brake_jerk(self, mdf, i)
            fcw_warning(self, mdf, i)

            
            self.kpi_table = self.kpi_table.round(3)
