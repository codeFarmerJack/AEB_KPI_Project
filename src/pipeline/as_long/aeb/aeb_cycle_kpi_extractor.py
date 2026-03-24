from src.pipeline.base.rule_based_cycle_kpi_extractor import RuleBasedCycleKpiExtractor
from src.pipeline.as_long.aeb.aeb_cycle_visualizer import AebCycleVisualizer


class AebCycleKpiExtractor(RuleBasedCycleKpiExtractor):
    """
    AEB cycle KPIs with explicit criteria (distance-weighted).

    Distance model:
    - dist[i] = egoSpeed[m/s] * dt, dt from time diff (non-negative).
    - KPI % = sum(dist where condition) / sum(dist) * 100.

    Availability KPIs:
    - AvailDistPct: aebPrecondBlkFromNdas == 0.
    - ROVAvail: aebInputHealthy == 1.
    - VALAvail: aebRunSetting == 2.
    - NoDegradation: aebDegradation == 1.

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
    SIGNAL_SPECS = {
        "time": {"signal": "time"},
        "speed_mps": {"signal": "egoSpeed"},
        "precond_blocked": {"signal": "aebPrecondBlkFromNdas"},
        "throttle": {"signal": "throttleValue"},
        "steer_angle": {"signal": "steerWheelAngleDeg"},
        "steer_rate": {"signal": "steerWheelAngleSpeedDeg"},
        "yaw_rate": {"signal": "yawRateDeg"},
        "lat_accel": {"signal": "latActAccel"},
        "aeb_input_healthy": {"signal": "aebInputHealthy", "required": False},
        "aeb_run_setting": {"signal": "aebRunSetting", "required": False},
        "aeb_degradation": {"signal": "aebDegradation", "required": False},
    }
    METRIC_SPECS = (
        {"key": "AvailDistPct", "signal": "precond_blocked", "op": "eq", "threshold": 0},
        {"key": "ROVAvail", "signal": "aeb_input_healthy", "op": "eq", "threshold": 1},
        {"key": "VALAvail", "signal": "aeb_run_setting", "op": "eq", "threshold": 2},
        {"key": "NoDegradation", "signal": "aeb_degradation", "op": "eq", "threshold": 1},
        {"key": "PedalPosProSuppression", "signal": "throttle", "op": "abs_gt", "calibratable": "PedalPosPro_th"},
        {"key": "SteeringWheelAngle", "signal": "steer_angle", "op": "abs_gt", "calibratable": "SteeringWheelAngle_Th"},
        {"key": "SteeringWheelAngleRate", "signal": "steer_rate", "op": "abs_gt", "calibratable": "AEB_SteeringAngleRate_Override"},
        {"key": "YawRate", "signal": "yaw_rate", "op": "abs_gt", "calibratable": "YawrateSuspension_Th"},
        {"key": "LatAccel", "signal": "lat_accel", "op": "abs_gt", "calibratable": "LateralAcceleration_th"},
        {"key": "LowSpeed", "signal": "speed_mps", "op": "lt", "threshold": _LOW_SPEED_MPS},
    )
