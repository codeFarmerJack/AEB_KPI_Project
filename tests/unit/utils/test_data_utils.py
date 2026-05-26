import numpy as np
import pandas as pd

from src.utils.data_utils import prune_unpopulated_columns_for_source


def test_roadcast_export_keeps_empty_schema_columns():
    df = pd.DataFrame(
        {
            "label": ["log.mf4"],
            "aebIntvStartTime": [np.nan],
            "aebSysRespTime": [np.nan],
        }
    )

    result = prune_unpopulated_columns_for_source(df, "roadcast_log")

    assert list(result.columns) == ["label", "aebIntvStartTime", "aebSysRespTime"]


def test_motion_1_export_drops_only_unpopulated_columns():
    df = pd.DataFrame(
        {
            "label": ["motion_1.mf4"],
            "feature": ["AEB"],
            "vehSpd": [42.0],
            "all_nan": [np.nan],
            "empty_text": [" "],
            "false_flag": [False],
            "zero_value": [0.0],
        }
    )
    df.attrs["display_names"] = {
        "label": "label",
        "feature": "feature",
        "vehSpd": "Vehicle Speed",
        "all_nan": "All NaN",
        "false_flag": "False Flag",
        "zero_value": "Zero Value",
    }

    result = prune_unpopulated_columns_for_source(df, "motion_1")

    assert list(result.columns) == [
        "label",
        "feature",
        "vehSpd",
        "false_flag",
        "zero_value",
    ]
    assert result.attrs["display_names"] == {
        "label": "label",
        "feature": "feature",
        "vehSpd": "Vehicle Speed",
        "false_flag": "False Flag",
        "zero_value": "Zero Value",
    }
