import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.viz.core.data_adapters import DataAdapters


def test_apply_reference_transform_supports_abs_syntax():
    values = np.array([-3.5, -1.0, 0.0, 2.0])

    transformed = DataAdapters.apply_reference_transform("abs(lsaebAverageAccel)", values)

    assert np.array_equal(transformed, np.array([3.5, 1.0, 0.0, 2.0]))


def test_base_reference_strips_abs_wrapper():
    assert DataAdapters.base_reference("abs(lsaebAverageAccel)") == "lsaebAverageAccel"
