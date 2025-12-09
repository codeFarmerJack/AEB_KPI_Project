import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass
from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.event_detector.as_long.aeb import find_aeb_intv_start, find_aeb_intv_end
from src.utils.process_calibratables import interpolate_threshold_clamped
from src.utils.data_utils import safe_scalar
from src.utils.kpis.as_long.aeb.brake_mode import AebBrakeModeCalculator
from src.utils.kpis.as_long.aeb.distance import AebDistanceCalculator
from src.utils.kpis.as_long.aeb.lat_accel import AebLatAccelCalculator
from src.utils.kpis.as_long.aeb.steering_wheel import AebSteeringCalculator
from src.utils.kpis.as_long.aeb.throttle import AebThrottleCalculator
from src.utils.kpis.as_long.aeb.yaw_rate import AebYawRateCalculator   
from src.utils.kpis.as_long.aeb.latency import AebLatencyCalculator 
from src.utils.signal_mdf import get_signal

# ------------------------------------------------------------------ #
# Threshold container
# ------------------------------------------------------------------ #
@dataclass
class Thresholds:
    steer_ang_th: float
    steer_ang_rate_th: float
    pedal_pos_inc_th: float
    yaw_rate_susp_th: float
    lat_accel_th: float


# ------------------------------------------------------------------ #
# AEB KPI Extractor
# ------------------------------------------------------------------ #
class AebEventKpiExtractor(BaseEventKpiExtractor):
    """Extracts AEB KPI metrics from MF4 chunks."""

    FEATURE_NAME = "AEB"
    PARAM_SPECS = {
        "pb_tgt_decel":           {"default": -6.0,  "type": float, "desc": "AEB PB target decel"},
        "fb_tgt_decel":          {"default": -15.0, "type": float, "desc": "AEB FB target decel"},
        "tgt_tol":                {"default": 0.2,   "type": float, "desc": "Target tolerance"},
        "aeb_end_thd":            {"default": -4.9,  "type": float, "desc": "AEB end threshold"},
        "time_idx_offset":        {"default": 300,   "type": int,   "desc": "Sample offset (~3s)"},
        "aeb_jerk_neg_thd":       {"default": -20.0, "type": float, "desc": "AEB negative jerk threshold (m/s³)"},
        "latency_window_samples": {"default": 30, "type": int, "desc": "Sample window after AEB start for latency detection"},
        "pb_duration":            {"default": 0.32,  "type": float, "desc": "Minimum duration (s) for partial braking"},
        "fb_jerk_neg_thd":        {"default": -20.0, "type": float, "desc": "FB negative jerk threshold (m/s³)"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_aeb_chunks", feature_name="AEB")

        # --- Load calibratables ---
        expected_keys = {
            "SteeringWheelAngle_Th": "SteeringWheelAngle_Th",
            "AEB_SteeringAngleRate_Override": "AEB_SteeringAngleRate_Override",
            "PedalPosProIncrease_Th": "PedalPosProIncrease_Th",
            "YawrateSuspension_Th": "YawrateSuspension_Th",
            "LateralAcceleration_th": "LateralAcceleration_th",
        }

        self.calibratables = {}
        for internal_name, cfg_key in expected_keys.items():
            if cfg_key in config.calibratables:
                self.calibratables[internal_name] = config.calibratables[cfg_key]
            else:
                warnings.warn(f"⚠️ Missing calibratable '{cfg_key}' in config.")
                self.calibratables[internal_name] = pd.DataFrame()

        self.latency_calc       = AebLatencyCalculator(self)
        self.brake_mode_calc    = AebBrakeModeCalculator(self)
        self.distance_calc      = AebDistanceCalculator(self)
        self.throttle_calc      = AebThrottleCalculator(self)
        self.steering_calc      = AebSteeringCalculator(self)
        self.yaw_rate_calc      = AebYawRateCalculator(self)
        self.lat_accel_calc     = AebLatAccelCalculator(self)

    # ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single AEB MF4 chunk.
        Returns a dict of KPI values to write into kpi_table.
        """

        result = {}

        # --- Time vector ---
        time = self._prepare_time(mdf)

        # --- Signals ---
        ego_speed     = get_signal(mdf, "egoSpeedKph")
        aeb_tgt_decel = get_signal(mdf, "aebTargetDecel")

        # --- AEB event detection ---
        try:
            aeb_start_idx, aeb_start_time = find_aeb_intv_start(
                {"aebTargetDecel": aeb_tgt_decel, "time": time},
                self.pb_tgt_decel
            )
            is_veh_stopped, aeb_end_idx, aeb_end_time = find_aeb_intv_end(
                {"egoSpeed": ego_speed, "aebTargetDecel": aeb_tgt_decel, "time": time},
                aeb_start_idx,
                self.aeb_end_thd
            )
        except Exception as e:
            warnings.warn(f"[{fname}] AEB event detection failed: {e}")
            return None

        # --- Save timing KPIs (returned to base class as dict) ---
        result["logTime"]          = safe_scalar(aeb_start_time)
        result["aebIntvStartTime"] = safe_scalar(aeb_start_time)
        result["aebIntvEndTime"]   = safe_scalar(aeb_end_time)
        result["isVehStopped"]     = bool(is_veh_stopped)

        # Duration KPI
        if np.isfinite(safe_scalar(aeb_start_time)) and np.isfinite(safe_scalar(aeb_end_time)):
            result["intvDur"] = round(float(aeb_end_time) - float(aeb_start_time), 3)

        # --- Vehicle speed at start ---
        veh_spd = np.nan
        if aeb_start_idx is not None and aeb_start_idx < len(ego_speed):
            veh_spd = safe_scalar(ego_speed[aeb_start_idx])
        result["vehSpd"] = veh_spd

        # --- Threshold interpolation ---
        thd = Thresholds(
            steer_ang_th      = interpolate_threshold_clamped(self.calibratables["SteeringWheelAngle_Th"], veh_spd),
            steer_ang_rate_th = interpolate_threshold_clamped(self.calibratables["AEB_SteeringAngleRate_Override"], veh_spd),
            pedal_pos_inc_th  = interpolate_threshold_clamped(self.calibratables["PedalPosProIncrease_Th"], veh_spd),
            yaw_rate_susp_th  = interpolate_threshold_clamped(self.calibratables["YawrateSuspension_Th"], veh_spd),
            lat_accel_th      = interpolate_threshold_clamped(self.calibratables["LateralAcceleration_th"], veh_spd),
        )

        # Save thresholds
        result["steerAngTh"]     = safe_scalar(thd.steer_ang_th)
        result["steerAngRateTh"] = safe_scalar(thd.steer_ang_rate_th)
        result["pedalPosIncTh"]  = safe_scalar(thd.pedal_pos_inc_th)
        result["yawRateSuspTh"]  = safe_scalar(thd.yaw_rate_susp_th)
        result["latAccelTh"]     = safe_scalar(thd.lat_accel_th)

        # --- KPI calculators (write directly into kpi_table) ---
        self.distance_calc.compute_distance(mdf, self.kpi_table, i, aeb_start_idx, aeb_end_idx)
        self.throttle_calc.compute_throttle(mdf, self.kpi_table, i, aeb_start_idx, thd.pedal_pos_inc_th)
        self.steering_calc.compute_steering(mdf, self.kpi_table, i, aeb_start_idx, thd.steer_ang_th, thd.steer_ang_rate_th)
        self.lat_accel_calc.compute_lat_accel(mdf, self.kpi_table, i, aeb_start_idx, thd.lat_accel_th)
        self.yaw_rate_calc.compute_yaw_rate(mdf, self.kpi_table, i, aeb_start_idx, thd.yaw_rate_susp_th)
        self.brake_mode_calc.compute_brake_mode(mdf, self.kpi_table, i, aeb_start_idx)
        self.latency_calc.compute_all(mdf, self.kpi_table, i, aeb_start_idx)

        return result
