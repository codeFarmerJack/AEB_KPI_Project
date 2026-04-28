import warnings

import numpy as np
import pandas as pd

from src.utils.kpis.as_long.actual_decel_onset import ActualDecelOnsetResolver
from src.utils.kpis.as_long.autonomous_braking_window import AutonomousBrakingWindowResolver
from src.utils.signal_mdf import get_signal


class BrakingStopDistanceCalculator:
    """Integrate ego speed across the autonomous-braking window and export centimeters."""

    _CM_PER_M = 100.0

    def __init__(self, extractor):
        self.extractor = extractor
        self.window_resolver = AutonomousBrakingWindowResolver(extractor)
        self.actual_onset_resolver = ActualDecelOnsetResolver(extractor)

    def compute_stop_distance(self, mdf, kpi_table, row_idx, column_name):
        if column_name not in kpi_table.columns:
            kpi_table[column_name] = pd.Series([np.nan] * len(kpi_table), dtype="float")

        window = self.window_resolver.resolve(
            mdf,
            row_idx=row_idx,
            column_name=column_name,
            require_speed_mps=True,
            stop_signal="ego_speed_mps",
            stop_mode="isclose",
            stop_value=0.0,
            stop_tolerance=1e-6,
        )
        if window is None:
            kpi_table.at[row_idx, column_name] = np.nan
            return

        long_accel = get_signal(mdf, "longActAccel")
        long_accel_flt = get_signal(mdf, "longActAccelFlt")
        accel_for_onset = (
            np.asarray(long_accel_flt, dtype=float)
            if long_accel_flt is not None
            else np.asarray(long_accel, dtype=float)
            if long_accel is not None
            else None
        )
        start_idx = window.start_idx
        if accel_for_onset is not None:
            min_len = min(len(accel_for_onset), len(window.time))
            accel_for_onset = accel_for_onset[:min_len]
            start_idx = self.actual_onset_resolver.resolve_start_idx(
                window.time[:min_len],
                accel_for_onset,
                window.start_idx,
                end_idx=min(window.stop_idx, min_len - 1),
                row_idx=row_idx,
                column_name=column_name,
                fallback_label="target decel edge",
            )

        if start_idx >= window.stop_idx:
            warnings.warn(f"[Row {row_idx}] {column_name}: invalid actual deceleration window")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        time_segment = window.time[start_idx : window.stop_idx + 1]
        speed_segment = window.ego_speed_mps[start_idx : window.stop_idx + 1]

        finite_mask = np.isfinite(time_segment) & np.isfinite(speed_segment)
        if np.count_nonzero(finite_mask) == 0:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: insufficient finite time/egoSpeed samples in braking window"
            )
            kpi_table.at[row_idx, column_name] = np.nan
            return

        time_segment = time_segment[finite_mask]
        speed_segment = speed_segment[finite_mask]
        if np.any(np.diff(time_segment) < 0):
            warnings.warn(f"[Row {row_idx}] {column_name}: non-monotonic time vector in braking window")
            kpi_table.at[row_idx, column_name] = np.nan
            return

        distance_m = self._trapezoid(speed_segment, time_segment)
        kpi_table.at[row_idx, column_name] = float(distance_m * self._CM_PER_M)

    @staticmethod
    def _trapezoid(y, x):
        if hasattr(np, "trapezoid"):
            return np.trapezoid(y, x)
        return np.trapz(y, x)
