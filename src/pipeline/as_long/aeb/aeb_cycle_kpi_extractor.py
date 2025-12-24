import os
import numpy as np
import warnings
from pathlib import Path

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor
from src.pipeline.as_long.aeb.aeb_cycle_visualizer import AebCycleVisualizer
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
            time              = get_signal(mdf, "time", required=True)
            speed_mps         = get_signal(mdf, "egoSpeed", required=True)
            precond_blocked   = get_signal(mdf, "aebPrecondBlk", required=True)
            throttle          = get_signal(mdf, "throttleValue", required=True)
            steer_angle       = get_signal(mdf, "steerWheelAngleDeg", required=True)
            steer_rate        = get_signal(mdf, "steerWheelAngleSpeedDeg", required=True)
            yaw_rate          = get_signal(mdf, "yawRateDeg", required=True)
            lat_accel         = get_signal(mdf, "latActAccel", required=True)
            aeb_input_healthy = get_signal(mdf, "aebInputHealthy", required=False)
            aeb_run_setting   = get_signal(mdf, "aebRunSetting", required=False)
            
        except AttributeError as e:
            warnings.warn(f"Missing required AEB signal: {e}")
            return {}

        # distance traveled per sample
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)

        dist       = speed_mps * dt
        total_dist = dist.sum()

        def _dist_pct_mask(mask):
            if mask is None:
                return np.nan
            mask = np.asarray(mask, bool)
            return float(np.sum(dist[mask]) / total_dist * 100)


        # KPI keys (include suppression breakdowns)
        kpi_keys = [
            "AvailDistPct",
            "aebROVAvail",
            "aebVALAvail",
            "PedalPosProSuppression",
            "SteeringWheelAngle",
            "SteeringWheelAngleRate",
            "YawRate",
            "LatAccel",
            "LowSpeed",
        ]

        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; availability cannot be computed.")
            return {self.FEATURE_NAME: {k: 0.0 for k in kpi_keys}}

        def _dist_pct_lt(signal, thresh):
            if signal is None or thresh is None:
                return np.nan

            s = np.asarray(signal, float)
            mask = s < thresh

            return float(np.sum(dist[mask]) / total_dist * 100)

        # ----- Suppression metrics ----- #
        def _dist_pct(signal, thresh):
            if signal is None or thresh is None:
                return np.nan

            # Convert to numpy arrays
            s = np.asarray(signal, dtype=float)
            t = np.asarray(thresh, dtype=float)

            # Magnitude-based suppression check
            mask = np.abs(s) > t

            return float(np.sum(dist[mask]) / total_dist * 100)

        suppress_pct = {}

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
        suppress_pct["LowSpeed"]               = round(_dist_pct_lt(speed_mps, 2/3.6), 2)

        # --- Feature availability (precondition-based) ---
        if precond_blocked is not None:
            precond_mask = (precond_blocked == 0)
            aeb_precond_avail = round(_dist_pct_mask(precond_mask), 2)
        else:
            aeb_precond_avail = np.nan

        # --- ROV availability ---
        if aeb_input_healthy is not None:
            rov_mask = (aeb_input_healthy == 1)
            aeb_rov_avail = round(_dist_pct_mask(rov_mask), 2)
        else:
            aeb_rov_avail = np.nan

        # --- VAL availability ---
        if aeb_run_setting is not None:
            val_mask = (aeb_run_setting == 2)
            aeb_val_avail = round(_dist_pct_mask(val_mask), 2)
        else:
            aeb_val_avail = np.nan

        metrics = {
            "AvailDistPct": aeb_precond_avail,
            "aebROVAvail": aeb_rov_avail,
            "aebVALAvail": aeb_val_avail,
            **suppress_pct,
        }

        return {self.FEATURE_NAME: {k: metrics.get(k, None) for k in kpi_keys}}

    # ------------------------------------------------------------------ #
    def render_cycle_dashboards(self, feature_name: str = "AEB"):
        """
        Generate per-file cycle dashboards using the feature-specific visualizer.
        """
        if self.cycle_kpi_table is None or self.cycle_kpi_table.empty:
            return

        out_dir = os.path.join(self.out_path_results, feature_name.lower(), "cycle")
        viz = AebCycleVisualizer(out_dir)

        viz.render_dashboards(
            self.cycle_kpi_table,
            feature_name,
            self.in_path_extracted,
            signal_extractor=viz.extract_cycle_signals,
        )
