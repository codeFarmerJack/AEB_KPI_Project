import numpy as np
import pandas as pd
import warnings
from src.utils.signal_mdf import get_signal


class AebSteeringCalculator:
    """
    Analyzes steering wheel behavior during an AEB event.

    KPIs extracted:
      • absSteerMaxDeg       - Maximum absolute steering angle (°)
      • isSteerHigh          - True if absSteerMaxDeg > steer_ang_th
      • absSteerRateMaxDeg   - Maximum absolute steering angle rate (°/s)
      • isSteerAngRateHigh   - True if absSteerRateMaxDeg > steer_ang_rate_th
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent AebEventKpiExtractor instance.
        """
        self.time_idx_offset = extractor.time_idx_offset  # e.g., 300 samples (~3s)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_steering(self, mdf, kpi_table, row_idx, aeb_start_idx,
                         steer_ang_th, steer_ang_rate_th):
        """
        Compute steering-related KPIs during an AEB event.
        Updates kpi_table in place.
        """
        # --- Step 1: Ensure required columns exist
        for col, default, dtype in [
            ("absSteerMaxDeg", np.nan, "float"),
            ("isSteerHigh", False, "bool"),
            ("absSteerRateMaxDeg", np.nan, "float"),
            ("isSteerAngRateHigh", False, "bool"),
        ]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

        # --- Step 2: Extract required signals (already in degrees)
        steer_angle = get_signal(mdf, "steerWheelAngleDeg")
        steer_rate  = get_signal(mdf, "steerWheelAngleSpeedDeg")
        if steer_angle is None or steer_rate is None:
            warnings.warn(f"[Row {row_idx}] Missing required steering signals")
            return

        # --- Step 3: Validate start index
        if aeb_start_idx is None or aeb_start_idx >= len(steer_angle):
            warnings.warn(f"[Row {row_idx}] Invalid AEB start index")
            return

        start_idx = max(0, aeb_start_idx - self.time_idx_offset)

        # --- Step 4: Compute steering angle metrics
        segment_angle = np.abs(steer_angle[start_idx:])
        if len(segment_angle) > 0:
            idx_rel = int(np.argmax(segment_angle))
            abs_steer_max_deg = round(float(segment_angle[idx_rel]), 2)
        else:
            abs_steer_max_deg = np.nan

        kpi_table.at[row_idx, "absSteerMaxDeg"] = abs_steer_max_deg
        kpi_table.at[row_idx, "isSteerHigh"] = (
            abs_steer_max_deg > steer_ang_th if np.isfinite(abs_steer_max_deg) else False
        )

        # --- Step 5: Compute steering rate metrics
        segment_rate = np.abs(steer_rate[start_idx:])
        if len(segment_rate) > 0:
            idx_rel_rate = int(np.argmax(segment_rate))
            abs_steer_rate_max_deg = round(float(segment_rate[idx_rel_rate]), 2)
        else:
            abs_steer_rate_max_deg = np.nan

        kpi_table.at[row_idx, "absSteerRateMaxDeg"] = abs_steer_rate_max_deg
        kpi_table.at[row_idx, "isSteerAngRateHigh"] = (
            abs_steer_rate_max_deg > steer_ang_rate_th if np.isfinite(abs_steer_rate_max_deg) else False
        )

        # --- Step 6: Debug print
        #print(
        #    f"🧭 [Row {row_idx}] Steering KPIs:\n"
        #    f"   • absSteerMaxDeg     = {abs_steer_max_deg if np.isfinite(abs_steer_max_deg) else 'NaN'}°\n"
        #    f"   • absSteerRateMaxDeg = {abs_steer_rate_max_deg if np.isfinite(abs_steer_rate_max_deg) else 'NaN'}°/s\n"
        #    f"   • Thresholds → Angle: {steer_ang_th:.1f}°, Rate: {steer_ang_rate_th:.1f}°/s\n"
        #)
