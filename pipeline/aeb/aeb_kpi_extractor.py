import os
import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass
from pipeline.base.base_kpi_extractor import BaseKpiExtractor
from utils.event_detector.aeb import find_aeb_intv_start, find_aeb_intv_end
from utils.process_calibratables import interpolate_threshold_clamped
from utils.data_utils import safe_scalar
from utils.kpis.aeb import *
from utils.kpis.aeb.latency_01 import AebLatencyCalculator


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
class AebKpiExtractor(BaseKpiExtractor):
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
        "pb_duration":            {"default": 0.32,  "type": float, "desc": "Minimum duration (s) for partial braking"}
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_detector):
        super().__init__(config, event_detector, "path_to_aeb_chunks", feature_name="AEB")

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

        self.latency_calc = AebLatencyCalculator(self)

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all AEB MF4 chunk files and calculate KPIs."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_chunks, fname)
            self._insert_label(i, fname)

            mdf = self._load_mdf(fpath)
            if mdf is None:
                continue

            # --- Time vector ---
            time = self._prepare_time(mdf)

            # --- Signals ---
            ego_speed = mdf.egoSpeedKph
            aeb_tgt_decel = mdf.aebTargetDecel

            # --- AEB event detection ---
            aeb_start_idx, aeb_start_time = find_aeb_intv_start(
                {"aebTargetDecel": aeb_tgt_decel, "time": time}, self.pb_tgt_decel
            )
            is_veh_stopped, aeb_end_idx, aeb_end_time = find_aeb_intv_end(
                {"egoSpeed": ego_speed, "aebTargetDecel": aeb_tgt_decel, "time": time},
                aeb_start_idx,
                self.aeb_end_thd,
            )

            # --- Save timing info ---
            self.kpi_table.loc[i, "logTime"]          = safe_scalar(aeb_start_time)
            self.kpi_table.loc[i, "aebIntvStartTime"] = safe_scalar(aeb_start_time)
            self.kpi_table.loc[i, "aebIntvEndTime"]   = safe_scalar(aeb_end_time)
            self.kpi_table.loc[i, "isVehStopped"]     = bool(is_veh_stopped)

            if np.isfinite(safe_scalar(aeb_start_time)) and np.isfinite(safe_scalar(aeb_end_time)):
                self.kpi_table.loc[i, "intvDur"] = round(float(aeb_end_time) - float(aeb_start_time), 3)

            # --- Vehicle speed at start ---
            veh_spd = np.nan
            if aeb_start_idx is not None and aeb_start_idx < len(ego_speed):
                veh_spd = safe_scalar(ego_speed[aeb_start_idx])
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- Threshold interpolation ---
            thd = Thresholds(
                steer_ang_th      = interpolate_threshold_clamped(self.calibratables["SteeringWheelAngle_Th"], veh_spd),
                steer_ang_rate_th = interpolate_threshold_clamped(self.calibratables["AEB_SteeringAngleRate_Override"], veh_spd),
                pedal_pos_inc_th  = interpolate_threshold_clamped(self.calibratables["PedalPosProIncrease_Th"], veh_spd),
                yaw_rate_susp_th  = interpolate_threshold_clamped(self.calibratables["YawrateSuspension_Th"], veh_spd),
                lat_accel_th      = interpolate_threshold_clamped(self.calibratables["LateralAcceleration_th"], veh_spd),
            )

            # --- Save thresholds ---
            self.kpi_table.loc[i, "steerAngTh"]     = safe_scalar(thd.steer_ang_th)
            self.kpi_table.loc[i, "steerAngRateTh"] = safe_scalar(thd.steer_ang_rate_th)
            self.kpi_table.loc[i, "pedalPosIncTh"]  = safe_scalar(thd.pedal_pos_inc_th)
            self.kpi_table.loc[i, "yawRateSuspTh"]  = safe_scalar(thd.yaw_rate_susp_th)
            self.kpi_table.loc[i, "latAccelTh"]     = safe_scalar(thd.lat_accel_th)

            # --- KPI computations ---
            
            distance(mdf, self.kpi_table, i, aeb_start_idx, aeb_end_idx)
            throttle(mdf, self.kpi_table, i, aeb_start_idx, thd.pedal_pos_inc_th)
            steering_wheel(mdf, self.kpi_table, i, aeb_start_idx, thd.steer_ang_th, thd.steer_ang_rate_th, self.time_idx_offset)
            lat_accel(mdf, self.kpi_table, i, aeb_start_idx, thd.lat_accel_th, self.time_idx_offset)
            yaw_rate(mdf, self.kpi_table, i, aeb_start_idx, thd.yaw_rate_susp_th, self.time_idx_offset)
            brake_mode(mdf, self.kpi_table, i, aeb_start_idx, self.pb_tgt_decel, self.fb_tgt_decel, self.tgt_tol)
            self.latency_calc.compute_all(mdf, self.kpi_table, i, aeb_start_idx)

            self.kpi_table = self.kpi_table.round(3)
