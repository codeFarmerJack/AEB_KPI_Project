import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.config import Config
from src.utils.process_calibratables import interpolate_threshold_clamped


def test_calibratable_cache_builds_xy_tuple():
    calibratables = {
        "TestCal": {"x": [0, 10], "y": [1, 3]},
        "NoneCal": None,
    }

    cache = Config._build_calibratable_cache(calibratables)

    assert "TestCal" in cache
    assert "NoneCal" not in cache
    x_vals, y_vals = cache["TestCal"]
    assert np.allclose(x_vals, [0, 10])
    assert np.allclose(y_vals, [1, 3])


def test_interpolate_threshold_accepts_tuple():
    table = (np.array([0, 10], dtype=float), np.array([1, 3], dtype=float))
    assert interpolate_threshold_clamped(table, 5.0) == 2.0
