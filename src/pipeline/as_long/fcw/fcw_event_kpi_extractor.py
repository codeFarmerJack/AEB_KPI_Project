import os
import numpy as np
import warnings
from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.event_detector.as_long.fcw import detect_fcw_events
from src.utils.data_utils import safe_scalar
from src.utils.kpis.as_long.fcw.brake_jerk import FcwBrakeJerkCalculator
from src.utils.kpis.as_long.fcw.fcw_warning import FcwWarningCalculator


# ------------------------------------------------------------------ #
# FCW KPI Extractor
# ------------------------------------------------------------------ #
class FcwEventKpiExtractor(BaseEventKpiExtractor):
    """Extracts FCW KPI metrics from MF4 chunks."""

    FEATURE_NAME = "FCW"
    PARAM_SPECS = {
        "window_s":               {"default": 1.0,   "type": float, "desc": "Sliding window duration (s)"},
        "brakejerk_jerk_neg_thd": {"default": -20.0, "type": float, "desc": "Negative jerk threshold (m/s³)"},
        "brakejerk_jerk_pos_thd": {"default": 20.0,  "type": float, "desc": "Positive jerk threshold (m/s³)"},
        "brakejerk_min_speed":    {"default": 30.0,  "type": float, "desc": "Minimum valid speed (kph)"},
        "brakejerk_max_speed":    {"default": 130.0, "type": float, "desc": "Maximum valid speed (kph)"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_fcw_chunks", feature_name="FCW")

        # --- Initialize submodules ---
        self.brake_jerk_calc    = FcwBrakeJerkCalculator(self)
        self.fcw_warning_calc   = FcwWarningCalculator(self)

    # ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single FCW MF4 file.
        Returns a dict of KPI values to write into kpi_table.
        """

        result = {}

        # --- Extract signals ---
        time        = self._prepare_time(mdf)
        accel       = mdf.longActAccelFlt
        fcw_request = mdf.fcwRequest
        ego_speed   = mdf.egoSpeedKph

        # Required signals missing
        if accel is None or fcw_request is None:
            warnings.warn(f"⚠️ Missing accel or fcwRequest in {fname} → skipped.")
            return None

        # --- FCW event detection ---
        try:
            start_times, end_times = detect_fcw_events(time, fcw_request)
        except Exception as e:
            warnings.warn(f"[{fname}] detect_fcw_events failed: {e}")
            return None

        if len(start_times) == 0:
            warnings.warn(f"⚠️ No FCW events detected in {fname}")
            return None

        # Use first event
        fcw_start_time = start_times[0]
        result["logTime"] = safe_scalar(fcw_start_time)

        # --- Vehicle speed at event start ---
        fcw_start_idx = int(np.argmin(np.abs(time - fcw_start_time)))
        veh_spd = safe_scalar(ego_speed[fcw_start_idx]) if ego_speed is not None else np.nan
        result["vehSpd"] = veh_spd

        # --- KPI computations (these write directly into kpi_table) ---
        self.brake_jerk_calc.compute_brake_jerk(mdf, self.kpi_table, i)
        self.fcw_warning_calc.compute_fcw_warning(mdf, self.kpi_table, i)

        return result
