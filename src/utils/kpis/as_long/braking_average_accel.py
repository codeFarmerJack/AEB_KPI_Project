import warnings

import numpy as np
import pandas as pd

from src.utils.kpis.as_long.actual_decel_onset import ActualDecelOnsetResolver
from src.utils.kpis.as_long.autonomous_braking_window import AutonomousBrakingWindowResolver
from src.utils.signal_mdf import get_signal


class BrakingAverageAccelCalculator:
    """Compute time-weighted average longitudinal acceleration over the braking window."""

    def __init__(self, extractor):
        self.extractor = extractor
        self.window_resolver = AutonomousBrakingWindowResolver(extractor)
        self.actual_onset_resolver = ActualDecelOnsetResolver(extractor)

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

        long_accel = get_signal(mdf, "longActAccel")
        long_accel_flt = get_signal(mdf, "longActAccelFlt")
        if long_accel is None:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: missing required signal(s): longActAccel"
            )
            kpi_table.at[row_idx, column_name] = np.nan
            return

        window = self.window_resolver.resolve(
            mdf,
            row_idx=row_idx,
            column_name=column_name,
            require_brake_pedal_released=True,
            require_speed_kph=True,
            stop_signal="ego_speed_kph",
            stop_mode="lt",
            stop_value=0.05,
        )
        if window is None:
            kpi_table.at[row_idx, column_name] = np.nan
            return

        min_len = min(len(long_accel), len(window.time))
        if min_len < 2:
            warnings.warn(f"[Row {row_idx}] {column_name}: insufficient samples (min_len={min_len})")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        long_accel = np.asarray(long_accel[:min_len], dtype=float)
        long_accel_flt = (
            np.asarray(long_accel_flt[:min_len], dtype=float)
            if long_accel_flt is not None
            else long_accel
        )
        time = window.time[:min_len]
        vehicle_speed = window.ego_speed_kph[:min_len]
        start_idx = self._resolve_actual_start_idx(
            time,
            long_accel_flt,
            window.start_idx,
            end_idx=window.stop_idx,
            row_idx=row_idx,
            column_name=column_name,
        )
        end_idx = window.stop_idx

        if end_idx >= min_len:
            warnings.warn(f"[Row {row_idx}] {column_name}: invalid stop index after alignment")
            kpi_table.at[row_idx, column_name] = np.nan
            return
        if start_idx >= end_idx:
            warnings.warn(f"[Row {row_idx}] {column_name}: invalid actual deceleration window")
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

    def _resolve_actual_start_idx(
        self,
        time,
        accel_for_onset,
        request_start_idx,
        *,
        end_idx,
        row_idx,
        column_name,
    ):
        return self.actual_onset_resolver.resolve_start_idx(
            time,
            accel_for_onset,
            request_start_idx,
            end_idx=end_idx,
            row_idx=row_idx,
            column_name=column_name,
            fallback_label="target decel edge",
        )
