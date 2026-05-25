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
from src.utils.kpis.as_long.braking_stop_distance import BrakingStopDistanceCalculator
from src.utils.kpis.as_long.aeb.lat_accel import AebLatAccelCalculator
from src.utils.kpis.as_long.aeb.steering_wheel import AebSteeringCalculator
from src.utils.kpis.as_long.aeb.throttle import AebThrottleCalculator
from src.utils.kpis.as_long.aeb.yaw_rate import AebYawRateCalculator   
from src.utils.kpis.as_long.aeb.latency import AebLatencyCalculator 
from src.utils.kpis.as_long.aeb.impact_rel_speed import AebImpactRelSpeedCalculator
from src.utils.kpis.as_long.braking_average_accel import BrakingAverageAccelCalculator
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

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_aeb_chunks", feature_name="AEB")
        if str(getattr(config, "signal_source", "")).lower() in {"motion_1", "motion1"}:
            self.fb_tgt_decel = -11.0
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
        result["aebSuspDur"] = self._compute_susp_duration(signals)

        veh_spd = self._vehicle_speed_at_start(signals.get("ego_speed"), aeb_start_idx)
        result["vehSpd"] = veh_spd

        thd = self._interpolate_thresholds(veh_spd)
        self._write_thresholds(result, thd)
        self._run_calculators(mdf, i, aeb_start_idx, aeb_end_idx, thd)

        return result

    def _load_calibratables(self, config):
        calibratables = {}
        cached = getattr(config, "calibratables_interp", {}) or {}
        for internal_name, cfg_key in self._CALIBRATABLE_KEYS.items():
            if cfg_key in cached:
                calibratables[internal_name] = cached[cfg_key]
            elif cfg_key in config.calibratables:
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
        self.impact_rel_spd_calc = AebImpactRelSpeedCalculator(self)
        self.avg_accel_calc = BrakingAverageAccelCalculator(self)
        self.stop_distance_calc = BrakingStopDistanceCalculator(self)

    def _load_signals(self, mdf):
        time = self._prepare_time(mdf)
        return {
            "time": time,
            "ego_speed": get_signal(mdf, "egoSpeedKph"),
            "aeb_tgt_decel": get_signal(mdf, "aebTargetDecel"),
            "aeb_abort": get_signal(mdf, "aebAbortFromNdas"),
        }

    def _compute_susp_duration(self, signals):
        time = signals.get("time")
        aeb_tgt_decel = signals.get("aeb_tgt_decel")
        aeb_abort = signals.get("aeb_abort")

        if time is None or aeb_abort is None or aeb_tgt_decel is None:
            warnings.warn("aebSuspDur: missing time, aebTargetDecel, or aebAbortFromNdas signal.")
            return None

        t = np.asarray(time)
        tgt_decel = np.asarray(aeb_tgt_decel)
        abort = np.asarray(aeb_abort)

        lengths = [len(t), len(abort), len(tgt_decel)]
        min_len = min(lengths) if lengths else 0
        if min_len < 2:
            warnings.warn(f"aebSuspDur: insufficient samples (min_len={min_len}).")
            return None

        t = t[:min_len]
        abort = abort[:min_len]
        tgt_decel = tgt_decel[:min_len]

        abort_prev = abort[:-1]
        abort_next = abort[1:]
        abort_rise = (abort_prev == 0) & (abort_next == 1)

        decel_prev = tgt_decel[:-1]
        fb_tgt = getattr(self, "fb_tgt_decel", -15.0)
        pb_tgt = getattr(self, "pb_tgt_decel", -6.0)
        decel_match = (
            np.isclose(decel_prev, fb_tgt, atol=1e-3)
            | np.isclose(decel_prev, pb_tgt, atol=1e-3)
            | np.isclose(decel_prev, -5.0, atol=1e-3)
        )

        start_candidates = np.where(decel_match & abort_rise)[0]
        if start_candidates.size == 0:
            warnings.warn(
                "aebSuspDur: no start transition found "
                f"(decel_match={int(decel_match.sum())}, abort_rise={int(abort_rise.sum())})."
            )
            return None
        start_transition = int(start_candidates[0])
        start_idx = start_transition + 1

        abort_fall = (abort_prev == 1) & (abort_next == 0)
        end_candidates = np.where(abort_fall & (np.arange(min_len - 1) > start_transition))[0]
        if end_candidates.size == 0:
            warnings.warn(
                "aebSuspDur: no end transition found "
                f"(abort_fall={int(abort_fall.sum())}, start_transition={start_transition})."
            )
            return None
        end_idx = int(end_candidates[0]) + 1

        if not np.isfinite(t[start_idx]) or not np.isfinite(t[end_idx]):
            warnings.warn(
                f"aebSuspDur: non-finite time at indices (start={start_idx}, end={end_idx})."
            )
            return None
        return round(float(t[end_idx] - t[start_idx]), 3)

    def _detect_event(self, signals, fname):
        try:
            aeb_start_idx, aeb_start_time = find_aeb_intv_start(
                {"aebTargetDecel": signals.get("aeb_tgt_decel"), "time": signals.get("time")},
                self.pb_tgt_decel,
            )
            is_veh_stopped, aeb_end_idx, aeb_end_time = find_aeb_intv_end(
                {
                    "egoSpeed": signals.get("ego_speed"),
                    "aebTargetDecel": signals.get("aeb_tgt_decel"),
                    "time": signals.get("time"),
                },
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
        self.impact_rel_spd_calc.compute_impact_rel_speed(mdf, self.kpi_table, index)
        self.avg_accel_calc.compute_average_accel(
            mdf,
            self.kpi_table,
            index,
            "aebAverageAccel",
            min_speed_kph=10.0,
        )
        self.stop_distance_calc.compute_stop_distance(
            mdf,
            self.kpi_table,
            index,
            "brakeDistAeb",
        )
