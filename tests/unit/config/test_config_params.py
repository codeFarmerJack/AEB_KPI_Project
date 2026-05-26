import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config_loader import ConfigLoader
from src.utils.path_manager import get_resource


def test_parse_params_sheet_casts_types():
    params_df = pd.DataFrame(
        {
            "parameter": ["A", "B", "C", "D", "E"],
            "value": ["1", "2.5", "true", "foo", "7"],
            "type": ["int", "float", "bool", "string", ""],
        }
    )

    params, types = ConfigLoader._parse_params_sheet(params_df)

    assert params["a"] == 1
    assert params["b"] == 2.5
    assert params["c"] is True
    assert params["d"] == "foo"
    assert params["e"] == 7.0
    assert types["a"] == "int"
    assert types["b"] == "float"
    assert types["c"] == "bool"
    assert types["d"] == "string"


def test_graph_spec_contains_aeb_lsaeb_scatter_rows():
    graph_spec = pd.read_excel(get_resource("config/kpi_as_long.xlsx"), sheet_name="graphSpec")
    graph_spec.columns = graph_spec.columns.str.strip().str.lower()

    required = {
        "brakeDistAeb": {
            "feature": "AEB",
            "title": "AEB Stop Distance",
            "plottype": "scatter",
            "axis_name": "Distance (cm)",
            "min_axis_value": 0,
            "max_axis_value": 4000,
        },
        "brakeDistLsaeb": {
            "feature": "LSAEB",
            "title": "LSAEB Stop Distance",
            "plottype": "scatter",
            "axis_name": "Distance (cm)",
            "min_axis_value": 0,
            "max_axis_value": 200,
        },
        "lsaebAverageAccel": {
            "feature": "LSAEB",
            "title": "LSAEB Average Acceleration Magnitude",
            "plottype": "scatter",
            "axis_name": "Acceleration Magnitude (m/s2)",
            "min_axis_value": 0,
            "max_axis_value": 10,
        },
        "aebAverageAccel": {
            "feature": "AEB",
            "title": "AEB Average Acceleration Magnitude",
            "plottype": "scatter",
            "axis_name": "Acceleration Magnitude (m/s2)",
            "min_axis_value": 0,
            "max_axis_value": 15,
        },
    }

    for reference, expected in required.items():
        reference_match = (
            graph_spec["reference"] == reference
            if reference not in {"lsaebAverageAccel", "aebAverageAccel"}
            else graph_spec["reference"] == f"abs({reference})"
        )
        row = graph_spec.loc[reference_match]
        assert not row.empty, f"missing graphSpec row for {reference}"
        match = row.iloc[0]
        assert match["feature"] == expected["feature"]
        assert match["title"] == expected["title"]
        assert match["plottype"] == expected["plottype"]
        assert match["axis_name"] == expected["axis_name"]
        assert match["min_axis_value"] == expected["min_axis_value"]
        assert match["max_axis_value"] == expected["max_axis_value"]


def test_as_long_signal_map_contains_motion_1_mappings():
    signals = pd.read_excel(get_resource("config/kpi_as_long.xlsx"), sheet_name="vbRcSignals")
    signals.columns = signals.columns.str.strip()

    assert "MOTION_1" in signals.columns
    assert "MOTION_1_Unit" in signals.columns

    indexed = (
        signals.dropna(subset=["genericName"])
        .set_index("genericName")
    )
    mapping = indexed["MOTION_1"].dropna().to_dict()
    units = indexed["MOTION_1_Unit"].dropna().to_dict()

    assert mapping["egoSpeed"] == "VehicleSpeed"
    assert mapping["latActAccel"] == "A1"
    assert mapping["steerWheelAngle"] == "SteeringWheelAngle"
    assert mapping["steerWheelAngleSpeed"] == "SteeringWheelAngleSpeed"
    assert mapping["yawRate"] == "YawRate"
    assert mapping["aebTargetDecel"] == "DADCAxLmtIT4"
    assert mapping["fcwState"] == "FCWState"
    assert units["latActAccel"] == "m/s2"
    assert units["egoSpeed"] == "km/h"
    assert units["steerWheelAngle"] == "deg"
    assert units["steerWheelAngleSpeed"] == "deg/s"
    assert units["yawRate"] == "deg/s"
    assert units["brakePedalPressed"] == "enum"
    assert units["fcwState"] == "enum"
