import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace

from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.kpis.as_long.braking_stop_distance import BrakingStopDistanceCalculator


class DummyExtractor:
    aeb_jerk_neg_thd = -20.0
    latency_window_samples = 30


class DummyExtractorWithResample:
    def __init__(self, resample_rate=0.01):
        self.config = SimpleNamespace(params={"resample_rate": resample_rate})

    def _prepare_time(self, mdf):
        return BaseEventKpiExtractor._prepare_time(self, mdf)

    def _get_resample_interval_s(self):
        return BaseEventKpiExtractor._get_resample_interval_s(self)


class DummyMdf:
    def __init__(self, signals):
        self._injected = signals


def test_brake_distance_uses_request_edge_when_no_actual_onset_is_detected():
    calc = BrakingStopDistanceCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "time": np.array([0.0, 1.0, 2.0, 3.0]),
            "aebTargetDecel": np.array([0.0, -0.5, -0.4, 0.0]),
            "egoSpeed": np.array([12.0, 8.0, 4.0, 0.0]),
        }
    )

    calc.compute_stop_distance(mdf, kpi_table, 0, "brakeDistAeb")

    assert kpi_table.at[0, "brakeDistAeb"] == pytest.approx(800.0, rel=1e-9)


def test_brake_distance_is_time_weighted_for_uneven_samples():
    calc = BrakingStopDistanceCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "time": np.array([0.0, 0.2, 1.2, 3.2]),
            "aebTargetDecel": np.array([0.1, -0.3, -0.2, 0.0]),
            "egoSpeed": np.array([9.0, 5.0, 2.0, 0.0]),
        }
    )

    calc.compute_stop_distance(mdf, kpi_table, 0, "brakeDistLsaeb")

    expected_m = ((5.0 + 2.0) / 2.0) * 1.0 + ((2.0 + 0.0) / 2.0) * 2.0
    assert kpi_table.at[0, "brakeDistLsaeb"] == pytest.approx(expected_m * 100.0, rel=1e-9)


def test_brake_distance_can_fallback_to_ego_speed_kph_when_needed():
    calc = BrakingStopDistanceCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "time": np.array([0.0, 1.0, 2.0, 3.0]),
            "aebTargetDecel": np.array([0.0, -0.2, -0.2, 0.0]),
            "egoSpeedKph": np.array([28.8, 18.0, 7.2, 0.0]),
        }
    )

    calc.compute_stop_distance(mdf, kpi_table, 0, "brakeDistAeb")

    assert kpi_table.at[0, "brakeDistAeb"] == pytest.approx(450.0, rel=1e-9)


def test_brake_distance_uses_configured_100hz_step_for_synthesized_time():
    calc = BrakingStopDistanceCalculator(DummyExtractorWithResample(0.01))
    kpi_table = pd.DataFrame(index=[0])
    mdf = DummyMdf(
        {
            "aebTargetDecel": np.array([0.0, -0.2, -0.2, 0.0]),
            "egoSpeed": np.array([2.0, 1.0, 0.5, 0.0]),
        }
    )
    mdf._time = np.array([0.0, 1.0, 2.0, 3.0])
    mdf._time_is_synthesized = True

    calc.compute_stop_distance(mdf, kpi_table, 0, "brakeDistAeb")

    assert kpi_table.at[0, "brakeDistAeb"] == pytest.approx(1.0, rel=1e-9)


def test_brake_distance_starts_at_actual_decel_onset_not_target_decel_edge():
    calc = BrakingStopDistanceCalculator(DummyExtractor())
    kpi_table = pd.DataFrame(index=[0])

    time = np.round(np.arange(0.0, 0.61, 0.01), 2)
    target_decel = np.zeros_like(time)
    target_decel[10:] = -0.2

    long_accel_flt = np.zeros_like(time)
    long_accel_flt[28:51] = -3.0

    ego_speed = np.full_like(time, 2.0)
    ego_speed[51:] = 0.0

    mdf = DummyMdf(
        {
            "time": time,
            "aebTargetDecel": target_decel,
            "egoSpeed": ego_speed,
            "longActAccelFlt": long_accel_flt,
        }
    )

    calc.compute_stop_distance(mdf, kpi_table, 0, "brakeDistLsaeb")

    assert kpi_table.at[0, "brakeDistLsaeb"] == pytest.approx(47.0, abs=1e-9)
