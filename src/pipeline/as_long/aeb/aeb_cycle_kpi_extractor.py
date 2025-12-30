import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor
from src.pipeline.as_long.aeb.aeb_cycle_visualizer import AebCycleVisualizer
from src.utils.signal_mdf import get_signal
from src.utils.process_calibratables import interpolate_threshold_clamped


class AebCycleKpiExtractor(BaseCycleKpiExtractor):
    """
    AEB cycle KPIs with explicit criteria (distance-weighted).

    Distance model:
    - dist[i] = egoSpeed[m/s] * dt, dt from time diff (non-negative).
    - KPI % = sum(dist where condition) / sum(dist) * 100.

    Availability KPIs:
    - AvailDistPct: aebPrecondBlk == 0.
    - ROVAvail: aebInputHealthy == 1.
    - VALAvail: aebRunSetting == 2.

    Suppression KPIs (distance % where |signal| exceeds threshold):
    - PedalPosProSuppression: |throttleValue| > PedalPosPro_th(egoSpd).
    - SteeringWheelAngle: |steerWheelAngleDeg| > SteeringWheelAngle_Th(egoSpd).
    - SteeringWheelAngleRate: |steerWheelAngleSpeedDeg| > AEB_SteeringAngleRate_Override(egoSpd).
    - YawRate: |yawRateDeg| > YawrateSuspension_Th(egoSpd).
    - LatAccel: |latActAccel| > LateralAcceleration_th(egoSpd).
    - LowSpeed: egoSpeed < 2 km/h (2/3.6 m/s).
    """

    FEATURE_NAME = "AEB"
    CYCLE_VISUALIZER_CLS = AebCycleVisualizer
    _LOW_SPEED_MPS = 2 / 3.6
    _SIGNAL_SPECS = {
        "time": ("time", True),
        "speed_mps": ("egoSpeed", True),
        "precond_blocked": ("aebPrecondBlk", True),
        "throttle": ("throttleValue", True),
        "steer_angle": ("steerWheelAngleDeg", True),
        "steer_rate": ("steerWheelAngleSpeedDeg", True),
        "yaw_rate": ("yawRateDeg", True),
        "lat_accel": ("latActAccel", True),
        "aeb_input_healthy": ("aebInputHealthy", False),
        "aeb_run_setting": ("aebRunSetting", False),
    }
    _AVAIL_SPECS = (
        {"key": "AvailDistPct", "signal": "precond_blocked", "op": "eq", "value": 0},
        {"key": "ROVAvail", "signal": "aeb_input_healthy", "op": "eq", "value": 1},
        {"key": "VALAvail", "signal": "aeb_run_setting", "op": "eq", "value": 2},
    )
    _SUPPRESSION_SPECS = (
        {"key": "PedalPosProSuppression", "signal": "throttle", "op": "abs_gt", "calibratable": "PedalPosPro_th"},
        {"key": "SteeringWheelAngle", "signal": "steer_angle", "op": "abs_gt", "calibratable": "SteeringWheelAngle_Th"},
        {"key": "SteeringWheelAngleRate", "signal": "steer_rate", "op": "abs_gt", "calibratable": "AEB_SteeringAngleRate_Override"},
        {"key": "YawRate", "signal": "yaw_rate", "op": "abs_gt", "calibratable": "YawrateSuspension_Th"},
        {"key": "LatAccel", "signal": "lat_accel", "op": "abs_gt", "calibratable": "LateralAcceleration_th"},
        {"key": "LowSpeed", "signal": "speed_mps", "op": "lt", "threshold": _LOW_SPEED_MPS},
    )

    def __init__(self, input_handler, config):
        super().__init__(input_handler, config)

    @dataclass(frozen=True)
    class _AebSignals:
        time: np.ndarray
        speed_mps: np.ndarray
        precond_blocked: np.ndarray
        throttle: np.ndarray
        steer_angle: np.ndarray
        steer_rate: np.ndarray
        yaw_rate: np.ndarray
        lat_accel: np.ndarray
        aeb_input_healthy: Optional[np.ndarray]
        aeb_run_setting: Optional[np.ndarray]

    def extract_cycle_kpis(self, mdf, fname):
        """
        Compute distance-weighted AEB KPIs from cycle signals.

        Criteria: see class docstring for per-KPI conditions and thresholds.
        Calibrated thresholds are interpolated per-sample using ego speed.
        """
        signals = self._load_signals(mdf)
        if signals is None:
            return {}

        dist, total_dist = self._compute_distance(signals.time, signals.speed_mps)
        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; availability cannot be computed.")
            return {self.FEATURE_NAME: {k: 0.0 for k in self._kpi_keys()}}

        metrics = {}
        metrics.update(self._compute_availability(signals, dist, total_dist))
        metrics.update(self._compute_suppressions(signals, dist, total_dist))

        metrics = self._round_metrics(metrics, digits=2)
        return {self.FEATURE_NAME: metrics}

    def _load_signals(self, mdf):
        missing = []
        values = {}
        for field, (mdf_name, required) in self._SIGNAL_SPECS.items():
            try:
                values[field] = get_signal(mdf, mdf_name, required=required)
            except AttributeError:
                if required:
                    missing.append(mdf_name)
                values[field] = None

        if missing:
            warnings.warn(f"Missing required AEB signals: {', '.join(missing)}")
            return None

        return self._AebSignals(**values)

    def _compute_distance(self, time, speed_mps):
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)
        dist = speed_mps * dt
        return dist, float(dist.sum())

    def _kpi_keys(self):
        return [spec["key"] for spec in self._AVAIL_SPECS + self._SUPPRESSION_SPECS]

    def _interp_calibratable(self, name, speed_mps):
        cal = (self.config.calibratables or {}).get(name)
        if cal is None:
            return None
        try:
            return interpolate_threshold_clamped(cal, speed_mps)
        except Exception as e:
            warnings.warn(f"⚠️ Failed to interpolate calibratable '{name}': {e}")
            return None

    def _mask_for_op(self, signal, threshold, op):
        if signal is None or threshold is None:
            return None

        s = np.asarray(signal, dtype=float)
        t = np.asarray(threshold, dtype=float)

        if op == "abs_gt":
            return np.abs(s) > t
        if op == "lt":
            return s < t
        if op == "eq":
            return s == t
        raise ValueError(f"Unsupported op '{op}'")

    def _dist_pct_from_mask(self, dist, total_dist, mask):
        if mask is None or total_dist <= 0:
            return np.nan
        mask = np.asarray(mask, bool)
        return float(np.sum(dist[mask]) / total_dist * 100)

    def _compute_availability(self, signals, dist, total_dist):
        metrics = {}
        for spec in self._AVAIL_SPECS:
            signal = getattr(signals, spec["signal"])
            mask = self._mask_for_op(signal, spec["value"], spec["op"])
            metrics[spec["key"]] = self._dist_pct_from_mask(dist, total_dist, mask)
        return metrics

    def _compute_suppressions(self, signals, dist, total_dist):
        metrics = {}
        for spec in self._SUPPRESSION_SPECS:
            signal = getattr(signals, spec["signal"])
            if "calibratable" in spec:
                threshold = self._interp_calibratable(spec["calibratable"], signals.speed_mps)
            else:
                threshold = spec.get("threshold")
            mask = self._mask_for_op(signal, threshold, spec["op"])
            metrics[spec["key"]] = self._dist_pct_from_mask(dist, total_dist, mask)
        return metrics

    def _round_metrics(self, metrics, digits=2):
        return {k: self._round_pct(v, digits) for k, v in metrics.items()}

    def _round_pct(self, value, digits):
        if value is None:
            return np.nan
        try:
            if np.isnan(value):
                return np.nan
        except TypeError:
            return value
        return float(np.round(value, digits))

    # ------------------------------------------------------------------ #
