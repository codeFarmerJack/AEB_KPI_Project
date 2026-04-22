import numpy as np
import pandas as pd
import pytest

from src.utils.kpis.as_long.braking_average_accel import BrakingAverageAccelCalculator


class DummyExtractor:
    pass


class DummyMdf:
    def __init__(self, signals):
        self._injected = signals


def test_aeb_average_accel_uses_autonomous_braking_window():
    calc = BrakingAverageAccelCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "time": np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
            "aebTargetDecel": np.array([0.0, 0.0, -0.2, -0.6, -0.8, -0.3, 0.0]),
            "brakePedalPressed": np.array([0, 0, 0, 0, 0, 0, 0]),
            "egoSpeedKph": np.array([12.0, 11.5, 11.0, 6.0, 2.0, 0.04, 0.0]),
            "longActAccel": np.array([0.0, -0.1, -1.0, -2.0, -3.0, -4.0, 0.0]),
        }
    )

    calc.compute_average_accel(
        mdf,
        kpi_table,
        0,
        "aebAverageAccel",
        min_speed_kph=10.0,
    )

    assert kpi_table.at[0, "aebAverageAccel"] == -2.5


def test_aeb_average_accel_is_time_weighted_for_uneven_samples():
    calc = BrakingAverageAccelCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "time": np.array([0.0, 0.1, 0.2, 1.2, 3.2]),
            "aebTargetDecel": np.array([0.0, -0.2, -0.6, -0.3, 0.0]),
            "brakePedalPressed": np.array([0, 0, 0, 0, 0]),
            "egoSpeedKph": np.array([12.0, 11.0, 8.0, 2.0, 0.04]),
            "longActAccel": np.array([0.0, -1.0, -4.0, -4.0, -1.0]),
        }
    )

    calc.compute_average_accel(
        mdf,
        kpi_table,
        0,
        "aebAverageAccel",
        min_speed_kph=10.0,
    )

    assert kpi_table.at[0, "aebAverageAccel"] == pytest.approx(-9.25 / 3.1, rel=1e-9)


def test_lsaeb_average_accel_respects_speed_range_gate():
    calc = BrakingAverageAccelCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "time": np.array([0.0, 1.0, 2.0, 3.0, 4.0]),
            "aebTargetDecel": np.array([0.0, -0.2, -0.6, -0.3, 0.0]),
            "brakePedalPressed": np.array([0, 0, 0, 0, 0]),
            "egoSpeedKph": np.array([1.5, 1.0, 0.6, 0.04, 0.0]),
            "longActAccel": np.array([-0.2, -0.8, -1.5, -2.0, 0.0]),
        }
    )

    calc.compute_average_accel(
        mdf,
        kpi_table,
        0,
        "lsaebAverageAccel",
        min_speed_kph=2.0,
        max_speed_kph=10.0,
    )

    assert np.isnan(kpi_table.at[0, "lsaebAverageAccel"])
