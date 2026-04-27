import warnings

import numpy as np
import pandas as pd

from src.utils.kpis.as_long.autonomous_braking_window import AutonomousBrakingWindowResolver


class BrakingStopDistanceCalculator:
    """Integrate ego speed across the autonomous-braking window and export centimeters."""

    _CM_PER_M = 100.0

    def __init__(self, extractor):
        self.extractor = extractor
        self.window_resolver = AutonomousBrakingWindowResolver(extractor)

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

        time_segment = window.time[window.start_idx : window.stop_idx + 1]
        speed_segment = window.ego_speed_mps[window.start_idx : window.stop_idx + 1]

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
