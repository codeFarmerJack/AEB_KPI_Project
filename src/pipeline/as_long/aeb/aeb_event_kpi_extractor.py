import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

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
    """
    AEB event KPIs with explicit criteria.

    Event detection:
    - Start index/time: first sample where `aebTargetDecel` < pb_tgt_decel
      (tolerance 0.1 in find_aeb_intv_start).
    - End index/time: first sample after start where `aebTargetDecel` > aeb_end_thd,
      or `egoSpeedKph` == 0; if both, take the earlier; otherwise last sample.

    KPI criteria (timing and thresholds):
    - logTime, aebIntvStartTime: start time.
    - aebIntvEndTime: end time.
    - isVehStopped: True if speed hits 0 after start.
    - intvDur: aebIntvEndTime - aebIntvStartTime.
    - vehSpd: `egoSpeedKph` at start index.
    - steerAngTh/steerAngRateTh/pedalPosIncTh/yawRateSuspTh/latAccelTh:
      interpolate calibratables vs `vehSpd`.

    Distance KPIs (`longGap`, up to end index):
    - firstDetDist: first non-zero `longGap`.
    - stableDetDist: first sample of last continuous non-zero segment.
    - aebIntvDist: `longGap` at start index.
    - aebStopGap: `longGap` at end index.

    Throttle KPIs (`throttleValue`, from start index to end of chunk):
    - pedalPosAtStart: `throttleValue` at start.
    - pedalPosMax: max throttle after start.
    - pedalPosInc: pedalPosMax - pedalPosAtStart.
    - isPedalPosIncHigh: pedalPosInc > pedalPosIncTh.
    - isPedalOnAtStrt: pedalPosAtStart != 0.

    Steering KPIs (`steerWheelAngleDeg`, `steerWheelAngleSpeedDeg`):
    - Window: [start - time_idx_offset, end of chunk].
    - absSteerMaxDeg: max |steer angle| in window.
    - isSteerHigh: absSteerMaxDeg > steerAngTh.
    - absSteerRateMaxDeg: max |steer rate| in window.
    - isSteerAngRateHigh: absSteerRateMaxDeg > steerAngRateTh.

    Yaw KPIs (`yawRateDeg`):
    - Window: [start - time_idx_offset, end of chunk].
    - absYawRateMaxDeg: max |yaw rate| in window.
    - isYawRateHigh: absYawRateMaxDeg > yawRateSuspTh.

    Lateral accel KPIs (`latActAccelFlt`):
    - Window: [start - time_idx_offset, end of chunk].
    - absLatAccelMax: max |lat accel| in window.
    - isLatAccelHigh: absLatAccelMax > latAccelTh.

    Brake mode KPIs (`aebTargetDecel`, from start to end of chunk):
    - isPBOn: any sample within tgt_tol of pb_tgt_decel.
    - isFBOn: any sample within tgt_tol of fb_tgt_decel.
    - pbDur: duration of first PB segment before first FB.
    - fbDur: duration of FB segment.

    Latency KPIs (`longActAccelFlt`, `aebTargetDecel`):
    - aebSysRespTime: time of first jerk < aeb_jerk_neg_thd in
      [start, start + latency_window_samples].
    - aebDeadTime: aebSysRespTime - aebIntvStartTime.
    - commLatency: after PB segment >= pb_duration, find PB->FB transition,
      then first jerk < fb_jerk_neg_thd in the latency window; delta is commLatency.
    """

    FEATURE_NAME = "AEB"
    _CALIBRATABLE_KEYS = {
        "SteeringWheelAngle_Th": "SteeringWheelAngle_Th",
        "AEB_SteeringAngleRate_Override": "AEB_SteeringAngleRate_Override",
        "PedalPosProIncrease_Th": "PedalPosProIncrease_Th",
        "YawrateSuspension_Th": "YawrateSuspension_Th",
        "LateralAcceleration_th": "LateralAcceleration_th",
    }
    PARAM_SPECS = {
        "pb_tgt_decel":           {"default": -6.0,  "type": float, "desc": "AEB PB target decel"},
        "fb_tgt_decel":           {"default": -15.0, "type": float, "desc": "AEB FB target decel"},
        "tgt_tol":                {"default": 0.2,   "type": float, "desc": "Target tolerance"},
        "aeb_end_thd":            {"default": -4.9,  "type": float, "desc": "AEB end threshold"},
        "time_idx_offset":        {"default": 300,   "type": int,   "desc": "Sample offset (~3s)"},
        "aeb_jerk_neg_thd":       {"default": -20.0, "type": float, "desc": "AEB negative jerk threshold (m/s³)"},
        "latency_window_samples": {"default": 30, "type": int, "desc": "Sample window after AEB start for latency detection"},
        "pb_duration":            {"default": 0.32,  "type": float, "desc": "Minimum duration (s) for partial braking"},
        "fb_jerk_neg_thd":        {"default": -20.0, "type": float, "desc": "FB negative jerk threshold (m/s³)"},
    }

    @dataclass(frozen=True)
    class _AebSignals:
        time: np.ndarray
        ego_speed: np.ndarray
        aeb_tgt_decel: np.ndarray

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_aeb_chunks", feature_name="AEB")
        self.calibratables = self._load_calibratables(config)
        self._init_calculators()

    # ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single AEB MF4 chunk.
        Returns a dict of KPI values to write into kpi_table.
        """
        signals = self._load_signals(mdf)
        event = self._detect_event(signals, fname)
        if event is None:
            return None

        aeb_start_idx, aeb_start_time, aeb_end_idx, aeb_end_time, is_veh_stopped = event
        result = self._build_timing_result(aeb_start_time, aeb_end_time, is_veh_stopped)

        veh_spd = self._vehicle_speed_at_start(signals.ego_speed, aeb_start_idx)
        result["vehSpd"] = veh_spd

        thd = self._interpolate_thresholds(veh_spd)
        self._write_thresholds(result, thd)
        self._run_calculators(mdf, i, aeb_start_idx, aeb_end_idx, thd)

        return result

    def _load_calibratables(self, config):
        calibratables = {}
        for internal_name, cfg_key in self._CALIBRATABLE_KEYS.items():
            if cfg_key in config.calibratables:
                calibratables[internal_name] = config.calibratables[cfg_key]
            else:
                warnings.warn(f"⚠️ Missing calibratable '{cfg_key}' in config.")
                calibratables[internal_name] = pd.DataFrame()
        return calibratables

    def _init_calculators(self):
        self.latency_calc = AebLatencyCalculator(self)
        self.brake_mode_calc = AebBrakeModeCalculator(self)
        self.distance_calc = AebDistanceCalculator(self)
        self.throttle_calc = AebThrottleCalculator(self)
        self.steering_calc = AebSteeringCalculator(self)
        self.yaw_rate_calc = AebYawRateCalculator(self)
        self.lat_accel_calc = AebLatAccelCalculator(self)

    def _load_signals(self, mdf):
        time = self._prepare_time(mdf)
        ego_speed = get_signal(mdf, "egoSpeedKph")
        aeb_tgt_decel = get_signal(mdf, "aebTargetDecel")
        return self._AebSignals(time=time, ego_speed=ego_speed, aeb_tgt_decel=aeb_tgt_decel)

    def _detect_event(self, signals, fname):
        try:
            aeb_start_idx, aeb_start_time = find_aeb_intv_start(
                {"aebTargetDecel": signals.aeb_tgt_decel, "time": signals.time},
                self.pb_tgt_decel,
            )
            is_veh_stopped, aeb_end_idx, aeb_end_time = find_aeb_intv_end(
                {"egoSpeed": signals.ego_speed, "aebTargetDecel": signals.aeb_tgt_decel, "time": signals.time},
                aeb_start_idx,
                self.aeb_end_thd,
            )
        except Exception as e:
            warnings.warn(f"[{fname}] AEB event detection failed: {e}")
            return None

        return aeb_start_idx, aeb_start_time, aeb_end_idx, aeb_end_time, is_veh_stopped

    def _build_timing_result(self, start_time, end_time, is_veh_stopped):
        result = {
            "logTime": safe_scalar(start_time),
            "aebIntvStartTime": safe_scalar(start_time),
            "aebIntvEndTime": safe_scalar(end_time),
            "isVehStopped": bool(is_veh_stopped),
        }
        duration = self._compute_duration(start_time, end_time)
        if duration is not None:
            result["intvDur"] = duration
        return result

    def _compute_duration(self, start_time, end_time):
        start = safe_scalar(start_time)
        end = safe_scalar(end_time)
        if np.isfinite(start) and np.isfinite(end):
            return round(float(end) - float(start), 3)
        return None

    def _vehicle_speed_at_start(self, ego_speed, start_idx):
        if ego_speed is None:
            return np.nan
        if start_idx is None:
            return np.nan
        if start_idx < len(ego_speed):
            return safe_scalar(ego_speed[start_idx])
        return np.nan

    def _interpolate_thresholds(self, veh_spd):
        return Thresholds(
            steer_ang_th=interpolate_threshold_clamped(
                self.calibratables["SteeringWheelAngle_Th"], veh_spd
            ),
            steer_ang_rate_th=interpolate_threshold_clamped(
                self.calibratables["AEB_SteeringAngleRate_Override"], veh_spd
            ),
            pedal_pos_inc_th=interpolate_threshold_clamped(
                self.calibratables["PedalPosProIncrease_Th"], veh_spd
            ),
            yaw_rate_susp_th=interpolate_threshold_clamped(
                self.calibratables["YawrateSuspension_Th"], veh_spd
            ),
            lat_accel_th=interpolate_threshold_clamped(
                self.calibratables["LateralAcceleration_th"], veh_spd
            ),
        )

    def _write_thresholds(self, result, thresholds):
        result["steerAngTh"] = safe_scalar(thresholds.steer_ang_th)
        result["steerAngRateTh"] = safe_scalar(thresholds.steer_ang_rate_th)
        result["pedalPosIncTh"] = safe_scalar(thresholds.pedal_pos_inc_th)
        result["yawRateSuspTh"] = safe_scalar(thresholds.yaw_rate_susp_th)
        result["latAccelTh"] = safe_scalar(thresholds.lat_accel_th)

    def _run_calculators(self, mdf, index, start_idx, end_idx, thresholds):
        self.distance_calc.compute_distance(mdf, self.kpi_table, index, start_idx, end_idx)
        self.throttle_calc.compute_throttle(mdf, self.kpi_table, index, start_idx, thresholds.pedal_pos_inc_th)
        self.steering_calc.compute_steering(
            mdf,
            self.kpi_table,
            index,
            start_idx,
            thresholds.steer_ang_th,
            thresholds.steer_ang_rate_th,
        )
        self.lat_accel_calc.compute_lat_accel(mdf, self.kpi_table, index, start_idx, thresholds.lat_accel_th)
        self.yaw_rate_calc.compute_yaw_rate(mdf, self.kpi_table, index, start_idx, thresholds.yaw_rate_susp_th)
        self.brake_mode_calc.compute_brake_mode(mdf, self.kpi_table, index, start_idx)
        self.latency_calc.compute_all(mdf, self.kpi_table, index, start_idx)
