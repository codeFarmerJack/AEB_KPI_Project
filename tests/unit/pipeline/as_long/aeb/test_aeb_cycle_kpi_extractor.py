import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.as_long.aeb.aeb_cycle_kpi_extractor import AebCycleKpiExtractor


class DummyMdf:
    def __init__(self, data):
        self._injected = data


def test_aeb_cycle_kpis_keep_available_motion_1_metrics_when_optional_signals_missing():
    cfg = SimpleNamespace(
        cycle_kpi_list=None,
        calibratables={},
        calibratables_interp={
            "PedalPosPro_th": (np.array([0.0, 100.0]), np.array([50.0, 50.0])),
            "SteeringWheelAngle_Th": (np.array([0.0, 100.0]), np.array([30.0, 30.0])),
            "AEB_SteeringAngleRate_Override": (np.array([0.0, 100.0]), np.array([60.0, 60.0])),
            "YawrateSuspension_Th": (np.array([0.0, 100.0]), np.array([10.0, 10.0])),
            "LateralAcceleration_th": (np.array([0.0, 100.0]), np.array([4.0, 4.0])),
        },
    )
    extractor = AebCycleKpiExtractor.__new__(AebCycleKpiExtractor)
    extractor.config = cfg

    mdf = DummyMdf(
        {
            "time": np.array([0.0, 1.0, 2.0]),
            "egoSpeed": np.array([10.0, 10.0, 10.0]),
            "throttleValue": np.array([10.0, 80.0, 10.0]),
            "steerWheelAngleDeg": np.array([0.0, 45.0, 0.0]),
            "steerWheelAngleSpeedDeg": np.array([0.0, 80.0, 0.0]),
            "yawRateDeg": np.array([0.0, 12.0, 0.0]),
        }
    )

    result = extractor.extract_cycle_kpis(mdf, "motion_1_extracted.mf4")

    assert result["AEB"]["PedalPosProSuppression"] > 0
    assert result["AEB"]["SteeringWheelAngle"] > 0
    assert result["AEB"]["SteeringWheelAngleRate"] > 0
    assert result["AEB"]["YawRate"] > 0
    assert np.isnan(result["AEB"]["AvailDistPct"])
    assert np.isnan(result["AEB"]["LatAccel"])
