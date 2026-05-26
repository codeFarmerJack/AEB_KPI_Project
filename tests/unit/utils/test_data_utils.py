import numpy as np
import pandas as pd

from src.utils.data_utils import prune_unsupported_columns_for_source


def test_roadcast_export_keeps_empty_schema_columns():
    df = pd.DataFrame(
        {
            "label": ["log.mf4"],
            "aebIntvStartTime": [np.nan],
            "aebSysRespTime": [np.nan],
        }
    )

    result = prune_unsupported_columns_for_source(df, "roadcast_log")

    assert list(result.columns) == ["label", "aebIntvStartTime", "aebSysRespTime"]


def test_motion_1_event_export_keeps_supported_empty_kpi_columns():
    df = pd.DataFrame(
        {
            "label": ["motion_1.mf4"],
            "vehSpd": [42.0],
            "aebSysRespTime": [np.nan],
            "absSteerMaxDeg": [np.nan],
            "absLatAccelMax": [np.nan],
            "firstDetDist": [np.nan],
            "ImpactRelSpdKph": [0.0],
        }
    )
    df.attrs["display_names"] = {
        "label": "label",
        "vehSpd": "Vehicle Speed",
        "aebSysRespTime": "AEB Response Time",
        "absSteerMaxDeg": "Max Steering",
        "absLatAccelMax": "Max Lateral Acceleration",
        "firstDetDist": "First Detection Distance",
        "ImpactRelSpdKph": "Impact Relative Speed",
    }

    result = prune_unsupported_columns_for_source(
        df,
        "motion_1",
        feature_name="AEB",
        table_kind="event",
    )

    assert list(result.columns) == [
        "label",
        "vehSpd",
        "aebSysRespTime",
        "absSteerMaxDeg",
        "absLatAccelMax",
    ]
    assert result.attrs["display_names"] == {
        "label": "label",
        "vehSpd": "Vehicle Speed",
        "aebSysRespTime": "AEB Response Time",
        "absSteerMaxDeg": "Max Steering",
        "absLatAccelMax": "Max Lateral Acceleration",
    }


def test_motion_1_cycle_export_keeps_supported_metrics_even_when_empty():
    df = pd.DataFrame(
        {
            "label": ["motion_1.mf4"],
            "feature": ["AEB"],
            "AvailDistPct": [np.nan],
            "PedalPosProSuppression": [np.nan],
            "SteeringWheelAngle": [np.nan],
            "LatAccel": [np.nan],
            "LowSpeed": [0.0],
        }
    )

    result = prune_unsupported_columns_for_source(
        df,
        "motion_1",
        feature_name="AEB",
        table_kind="cycle",
    )

    assert list(result.columns) == [
        "label",
        "feature",
        "PedalPosProSuppression",
        "SteeringWheelAngle",
        "LatAccel",
        "LowSpeed",
    ]
