import os
import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass
from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.data_utils import safe_scalar
from src.utils.event_detector.as_lat.lka import detect_lka_events  
from src.utils.signal_mdf import get_signal


# ------------------------------------------------------------------ #
# LKA KPI Extractor
# ------------------------------------------------------------------ #
class LkaEventKpiExtractor(BaseEventKpiExtractor):
    """Extracts LKA (Lane Keeping Assist) KPI metrics."""

    FEATURE_NAME = "LKA"
    PARAM_SPECS = {
        "Driver_Interaction_Torque": {
            "default": 2.0,
            "type": float,
            "desc": "Threshold for driver interaction torque [Nm]",
        },
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_lka_chunks", feature_name="LKA")
        self.driver_torque_th = float(config.params.get("driver_interaction_torque", 2.0))

    # ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single LKA event segment.
        Returns a dict of KPI values to write into kpi_table.
        """

        result = {}

        # --- Extract signals ---
        try:
            time            = self._prepare_time(mdf)
            dtle            = get_signal(mdf, "dtle", required=True)
            dtle_target     = get_signal(mdf, "dtleTarget", default=np.full_like(dtle, np.nan))
            lka_status      = get_signal(mdf, "lkaInterventionStatus", required=True)
            steer_torque    = get_signal(mdf, "steerWheelTorque", required=True)
            RateOfDeparture = get_signal(mdf, "rateOfDeparture", required=True)
            VehCurvature    = get_signal(mdf, "vehCurvature", required=True)
            LaneCurvature   = get_signal(mdf, "laneCurvature", required=True)
            use_case        = get_signal(mdf, "useCase", default=np.full_like(dtle, np.nan))
            ego_speed       = get_signal(mdf, "egoSpeedKph", default=np.full_like(dtle, np.nan))
        except AttributeError as e:
            warnings.warn(f"[{fname}] Missing required signal: {e}")
            return None

        # --- Detect intervention events ---
        try:
            start_indices, end_indices = detect_lka_events(time, lka_status)
        except Exception as e:
            warnings.warn(f"[{fname}] detect_lka_events failed: {e}")
            return None

        if len(start_indices) == 0:
            warnings.warn(f"[{fname}] No LKA events detected.")
            return None

        # Use first event
        start_idx = int(start_indices[0])
        end_idx   = int(end_indices[0]) if len(end_indices) else len(time) - 1

        start_idx = max(0, min(start_idx, len(time) - 1))
        end_idx   = max(0, min(end_idx,   len(time) - 1))

        # --- Compute KPIs ---
        dtle_target_at_start = safe_scalar(dtle_target[start_idx])
        dtle_at_start        = safe_scalar(dtle[start_idx])
        
        dtle_min_during = np.nanmin(dtle[start_idx:end_idx+1])
        min_dtle_delta  = safe_scalar(dtle_target_at_start - dtle_min_during)

        RoD_at_start        = safe_scalar(RateOfDeparture[start_idx])
        Veh_Curv_at_start   = safe_scalar(VehCurvature[start_idx])
        Lane_Curv_at_start  = safe_scalar(LaneCurvature[start_idx])
        use_case_at_start   = safe_scalar(use_case[start_idx])
        veh_spd_at_start    = safe_scalar(ego_speed[start_idx])

        # Driver interaction torque test
        is_high = np.any(np.abs(steer_torque[start_idx:end_idx + 1]) > self.driver_torque_th)

        # --- Store results (these go back into the base class to fill table) ---
        result["logTime"]            = safe_scalar(time[start_idx])
        result["MinDTLEDelta"]       = min_dtle_delta
        result["TrigDTLE"]           = dtle_at_start
        result["isWhlTrqHigh"]       = bool(is_high)
        result["TrigRateOfDeparture"]= RoD_at_start
        result["TrigVehCurv"]        = Veh_Curv_at_start
        result["TrigLaneCurv"]       = Lane_Curv_at_start
        result["vehSpd"]             = veh_spd_at_start
        result["UseCase"]            = use_case_at_start

        return result
