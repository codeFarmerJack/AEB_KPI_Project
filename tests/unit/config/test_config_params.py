import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config_loader import ConfigLoader


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
