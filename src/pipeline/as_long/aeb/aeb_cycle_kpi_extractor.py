import numpy as np
import warnings

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor
from src.utils.signal_mdf import get_signal


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
            throttle        = get_signal(mdf, "throttleValue", required=True)
            steer_angle     = get_signal(mdf, "steerWheelAngle", required=True)
            steer_rate      = get_signal(mdf, "steerWheelAngleSpeed", required=True)
            yaw_rate        = get_signal(mdf, "yawRate", required=True)
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
        def _interp_thresh(curve_name):
            curve = (self.config.calibratables or {}).get(curve_name, None)
            if not curve or "x" not in curve or "y" not in curve:
                return None
            try:
                x = np.asarray(curve["x"], dtype=float)
                y = np.asarray(curve["y"], dtype=float)
                return np.interp(speed_mps, x, y, left=y[0], right=y[-1])
            except Exception:
                return None

        def _dist_pct(signal, thresh):
            if signal is None or thresh is None:
                return np.nan
            mask = np.asarray(signal, dtype=float) > np.asarray(thresh, dtype=float)
            return float(np.sum(dist[mask]) / total_dist * 100)

        suppress_masks = []
        suppress_pct = {}

        # Precondition block flag as a suppression
        if precond_blocked is not None:
            mask_precond = precond_blocked != 0
            suppress_masks.append(mask_precond)
        else:
            mask_precond = None

        # Threshold-based suppressions
        thr_pedal  = _interp_thresh("PedalPosPro_th")
        thr_steer  = _interp_thresh("SteeringWheelAngle_Th")
        thr_rate   = _interp_thresh("AEB_SteeringAngleRate_Override")
        thr_yaw    = _interp_thresh("YawrateSuspension_Th")
        thr_lat    = _interp_thresh("LateralAcceleration_th")

        suppress_pct["PedalPosProSuppression"] = round(_dist_pct(throttle, thr_pedal), 2) if throttle is not None and thr_pedal is not None else np.nan
        suppress_pct["SteeringWheelAngle"]     = round(_dist_pct(steer_angle, thr_steer), 2) if steer_angle is not None and thr_steer is not None else np.nan
        suppress_pct["SteeringWheelAngleRate"] = round(_dist_pct(steer_rate, thr_rate), 2) if steer_rate is not None and thr_rate is not None else np.nan
        suppress_pct["YawRate"]                = round(_dist_pct(yaw_rate, thr_yaw), 2) if yaw_rate is not None and thr_yaw is not None else np.nan
        suppress_pct["LatAccel"]               = round(_dist_pct(lat_accel, thr_lat), 2) if lat_accel is not None and thr_lat is not None else np.nan

        # Build combined availability mask = NOT(any suppression)
        if thr_pedal is not None and throttle is not None:
            suppress_masks.append(np.asarray(throttle, dtype=float) > thr_pedal)
        if thr_steer is not None and steer_angle is not None:
            suppress_masks.append(np.asarray(steer_angle, dtype=float) > thr_steer)
        if thr_rate is not None and steer_rate is not None:
            suppress_masks.append(np.asarray(steer_rate, dtype=float) > thr_rate)
        if thr_yaw is not None and yaw_rate is not None:
            suppress_masks.append(np.asarray(yaw_rate, dtype=float) > thr_yaw)
        if thr_lat is not None and lat_accel is not None:
            suppress_masks.append(np.asarray(lat_accel, dtype=float) > thr_lat)

        if suppress_masks:
            suppress_union = suppress_masks[0]
            for m in suppress_masks[1:]:
                suppress_union = suppress_union | m
            avail_mask = ~suppress_union
        else:
            # fallback to precond flag only if no suppressions available
            avail_mask = precond_blocked == 0 if precond_blocked is not None else np.ones_like(speed_mps, dtype=bool)

        enabled_dist = np.sum(dist[avail_mask])
        pct_avail    = enabled_dist / total_dist * 100

        metrics = {
            "AvailDistPct": round(pct_avail, 2),
            **suppress_pct,
        }

        return {self.FEATURE_NAME: {k: metrics.get(k, None) for k in kpi_keys}}
