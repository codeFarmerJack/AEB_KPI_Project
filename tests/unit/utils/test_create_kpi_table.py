import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.create_kpi_table import create_kpi_table_from_df


def test_create_kpi_table_normalizes_schema_and_feature():
    schema_df = pd.DataFrame(
        {
            " Feature ": [" Common ", "AEB "],
            " Name ": ["vehSpd", "aebIntvDist"],
            " Type ": ["double", "double"],
            " Unit ": ["km/h", "m"],
        }
    )

    df = create_kpi_table_from_df(schema_df, feature="aeb")

    assert list(df.columns) == ["vehSpd", "aebIntvDist"]
    assert df.attrs["display_names"]["vehSpd"] == "vehSpd [km/h]"
    assert df.attrs["display_names"]["aebIntvDist"] == "aebIntvDist [m]"


def test_create_kpi_table_display_names_handle_empty_units():
    schema_df = pd.DataFrame(
        {
            "Feature": ["COMMON", "COMMON"],
            "Name": ["flag", "score"],
            "Type": ["logical", "double"],
            "Unit": ["", None],
        }
    )

    df = create_kpi_table_from_df(schema_df)

    assert df.attrs["display_names"]["flag"] == "flag"
    assert df.attrs["display_names"]["score"] == "score"
