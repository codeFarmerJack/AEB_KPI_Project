import numpy as np
import warnings

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor
from src.utils.signal_mdf import get_signal
from src.utils.process_calibratables import interpolate_threshold_clamped


class AebCycleKpiExtractor(BaseCycleKpiExtractor):
    """
    Computes AEB availability KPI:
      - AvailDistPct: percentage of traveled distance where AEB is available
    """

    FEATURE_NAME = "AEB"

    def __init__(self, input_handler, config):
        super().__init__(input_handler, config)

    def extract_cycle_kpis(self, mdf, fname):
        """
        Availability condition:
            Feature is available only when NONE of the suppression masks are true.

        Suppression reasons (distance % each):
            - PedalPosProSuppression: throttleValue > PedalPosPro_th(egoSpd)
            - SteeringWheelAngle: steerWheelAngle > SteeringWheelAngle_Th(egoSpd)
            - SteeringWheelAngleRate: steerWheelAngleSpeed > AEB_SteeringAngleRate_Override(egoSpd)
            - YawRate: yawRate > YawrateSuspension_Th(egoSpd)
            - LatAccel: latActAccel > LateralAcceleration_th(egoSpd)
            - aebPrecondBlk != 0 (if provided)
        """
        try:
            time            = get_signal(mdf, "time", required=True)
            speed_mps       = get_signal(mdf, "egoSpeed", required=True)
            precond_blocked = get_signal(mdf, "aebPrecondBlk", required=True)
            throttle        = get_signal(mdf, "throttleValuePct", required=True)
            steer_angle     = get_signal(mdf, "steerWheelAngleDeg", required=True)
            steer_rate      = get_signal(mdf, "steerWheelAngleSpeedDeg", required=True)
            yaw_rate        = get_signal(mdf, "yawRateDeg", required=True)
            lat_accel       = get_signal(mdf, "latActAccel", required=True)
        except AttributeError as e:
            warnings.warn(f"Missing required AEB signal: {e}")
            return {}

        # distance traveled per sample
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)

        dist       = speed_mps * dt
        total_dist = dist.sum()

        # KPI keys (include suppression breakdowns)
        kpi_keys = [
            "AvailDistPct",
            "PedalPosProSuppression",
            "SteeringWheelAngle",
            "SteeringWheelAngleRate",
            "YawRate",
            "LatAccel",
        ]

        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; availability cannot be computed.")
            return {self.FEATURE_NAME: {k: 0.0 for k in kpi_keys}}

        # ----- Suppression metrics ----- #
        def _dist_pct(signal, thresh):
            if signal is None or thresh is None:
                return np.nan
            mask = np.asarray(signal, dtype=float) > np.asarray(thresh, dtype=float)
            return float(np.sum(dist[mask]) / total_dist * 100)

        suppress_masks = []
        suppress_pct = {}

        # Precondition block flag as a suppression
        if precond_blocked is None:
            warnings.warn("⚠️ Missing aebPrecondBlk signal — availability cannot be computed.")
            avail_mask = np.zeros_like(speed_mps, dtype=bool)
        else:
            avail_mask = (precond_blocked == 0)


        # Threshold-based suppressions (vectorized per-sample interpolation)
        def _safe_interp(name):
            cal = (self.config.calibratables or {}).get(name)
            if cal is None:
                return None
            try:
                return interpolate_threshold_clamped(cal, speed_mps)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to interpolate calibratable '{name}': {e}")
                return None

        pedal_thd      = _safe_interp("PedalPosPro_th")
        steer_thd      = _safe_interp("SteeringWheelAngle_Th")
        steer_rate_thd = _safe_interp("AEB_SteeringAngleRate_Override")
        yaw_rate_thd   = _safe_interp("YawrateSuspension_Th")
        lat_accel_thd  = _safe_interp("LateralAcceleration_th")

        suppress_pct["PedalPosProSuppression"] = round(_dist_pct(throttle, pedal_thd), 2) if throttle is not None and pedal_thd is not None else np.nan
        suppress_pct["SteeringWheelAngle"]     = round(_dist_pct(steer_angle, steer_thd), 2) if steer_angle is not None and steer_thd is not None else np.nan
        suppress_pct["SteeringWheelAngleRate"] = round(_dist_pct(steer_rate, steer_rate_thd), 2) if steer_rate is not None and steer_rate_thd is not None else np.nan
        suppress_pct["YawRate"]                = round(_dist_pct(yaw_rate, yaw_rate_thd), 2) if yaw_rate is not None and yaw_rate_thd is not None else np.nan
        suppress_pct["LatAccel"]               = round(_dist_pct(lat_accel, lat_accel_thd), 2) if lat_accel is not None and lat_accel_thd is not None else np.nan
        
        enabled_dist = np.sum(dist[avail_mask])
        pct_avail    = enabled_dist / total_dist * 100

        metrics = {
            "AvailDistPct": round(pct_avail, 2),
            **suppress_pct,
        }

        return {self.FEATURE_NAME: {k: metrics.get(k, None) for k in kpi_keys}}
