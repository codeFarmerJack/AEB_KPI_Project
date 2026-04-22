import warnings

import numpy as np
import pandas as pd

from src.utils.signal_mdf import get_signal


class BrakingAverageAccelCalculator:
    """Compute time-weighted average longitudinal acceleration over the braking window."""

    def __init__(self, extractor):
        self.extractor = extractor

    def compute_average_accel(
        self,
        mdf,
        kpi_table,
        row_idx,
        column_name,
        *,
        min_speed_kph=None,
        max_speed_kph=None,
    ):
        if column_name not in kpi_table.columns:
            kpi_table[column_name] = pd.Series([np.nan] * len(kpi_table), dtype="float")

        time = get_signal(mdf, "time")
        if time is None and hasattr(self.extractor, "_prepare_time"):
            time = self.extractor._prepare_time(mdf)
        target_decel = get_signal(mdf, "aebTargetDecel")
        brake_pedal = get_signal(mdf, "brakePedalPressed")
        vehicle_speed = get_signal(mdf, "egoSpeedKph")
        long_accel = get_signal(mdf, "longActAccel")

        required = {
            "time": time,
            "aebTargetDecel": target_decel,
            "brakePedalPressed": brake_pedal,
            "egoSpeedKph": vehicle_speed,
            "longActAccel": long_accel,
        }
        missing = [name for name, signal in required.items() if signal is None]
        if missing:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: missing required signal(s): {', '.join(missing)}"
            )
            kpi_table.at[row_idx, column_name] = np.nan
            return

        min_len = min(len(signal) for signal in required.values())
        if min_len < 2:
            warnings.warn(f"[Row {row_idx}] {column_name}: insufficient samples (min_len={min_len})")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        time = np.asarray(time[:min_len], dtype=float)
        target_decel = np.asarray(target_decel[:min_len], dtype=float)
        brake_pedal = np.asarray(brake_pedal[:min_len], dtype=float)
        vehicle_speed = np.asarray(vehicle_speed[:min_len], dtype=float)
        long_accel = np.asarray(long_accel[:min_len], dtype=float)

        start_idx = self._find_start_idx(target_decel, brake_pedal)
        if start_idx is None:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: no aebTargetDecel falling edge found with brakePedalPressed == 0"
            )
            kpi_table.at[row_idx, column_name] = np.nan
            return

        start_speed = vehicle_speed[start_idx]
        if not np.isfinite(start_speed) or not self._speed_in_range(
            start_speed,
            min_speed_kph=min_speed_kph,
            max_speed_kph=max_speed_kph,
        ):
            kpi_table.at[row_idx, column_name] = np.nan
            return

        rel_stop_idx = np.flatnonzero(vehicle_speed[start_idx:] < 0.05)
        if rel_stop_idx.size == 0:
            warnings.warn(f"[Row {row_idx}] {column_name}: vehicle never reached egoSpeedKph < 0.05")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        end_idx = start_idx + int(rel_stop_idx[0])
        time_segment = time[start_idx : end_idx + 1]
        accel_segment = long_accel[start_idx : end_idx + 1]
        finite_mask = np.isfinite(time_segment) & np.isfinite(accel_segment)
        if np.count_nonzero(finite_mask) < 2:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: insufficient finite time/longActAccel samples in braking window"
            )
            kpi_table.at[row_idx, column_name] = np.nan
            return

        time_segment = time_segment[finite_mask]
        accel_segment = accel_segment[finite_mask]
        if np.any(np.diff(time_segment) < 0):
            warnings.warn(f"[Row {row_idx}] {column_name}: non-monotonic time vector in braking window")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        duration = float(time_segment[-1] - time_segment[0])
        if duration <= 0:
            warnings.warn(f"[Row {row_idx}] {column_name}: non-positive braking duration")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        integral = self._trapezoid(accel_segment, time_segment)
        kpi_table.at[row_idx, column_name] = float(integral / duration)

    @staticmethod
    def _find_start_idx(target_decel, brake_pedal):
        falling_edge = (target_decel[:-1] >= 0.0) & (target_decel[1:] < 0.0)
        pedal_not_pressed = np.isclose(brake_pedal[1:], 0.0, atol=1e-6)
        candidates = np.flatnonzero(falling_edge & pedal_not_pressed)
        if candidates.size == 0:
            return None
        return int(candidates[0] + 1)

    @staticmethod
    def _speed_in_range(speed_kph, *, min_speed_kph=None, max_speed_kph=None):
        if min_speed_kph is not None and not speed_kph > min_speed_kph:
            return False
        if max_speed_kph is not None and not speed_kph <= max_speed_kph:
            return False
        return True

    @staticmethod
    def _trapezoid(y, x):
        if hasattr(np, "trapezoid"):
            return np.trapezoid(y, x)
        return np.trapz(y, x)
