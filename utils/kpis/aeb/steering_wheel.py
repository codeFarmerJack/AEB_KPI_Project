import numpy as np
import pandas as pd
import warnings


class AebSteeringCalculator:
    """
    Analyzes steering wheel behavior during an AEB event.

    KPIs extracted:
      • absSteerMaxDeg       – Maximum absolute steering angle (°)
      • isSteerHigh          – True if absSteerMaxDeg > steer_ang_th
      • absSteerRateMaxDeg   – Maximum absolute steering angle rate (°/s)
      • isSteerAngRateHigh   – True if absSteerRateMaxDeg > steer_ang_rate_th

    Constructed from an AebKpiExtractor instance:

        self.steering_calc = AebSteeringCalculator(self)

    Called within the KPI loop:

        self.steering_calc.compute_steering(
            mdf, self.kpi_table, i, aeb_start_idx
        )
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent AebKpiExtractor instance.
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

        # --- Step 2: Extract required signals
        try:
            steer_angle = np.asarray(mdf.steerWheelAngle)
            steer_rate = np.asarray(mdf.steerWheelAngleSpeed)
        except AttributeError:
            warnings.warn(f"[Row {row_idx}] Missing required steering signals")
            return

        # --- Step 3: Validate start index
        if aeb_start_idx is None or aeb_start_idx >= len(steer_angle):
            warnings.warn(f"[Row {row_idx}] Invalid AEB start index")
            return

        start_idx = max(0, aeb_start_idx - self.time_idx_offset)

        # --- Step 4: Compute steering angle metrics
        segment_angle = steer_angle[start_idx:]
        if len(segment_angle) > 0:
            idx_rel = int(np.argmax(np.abs(segment_angle)))
            steer_max = float(segment_angle[idx_rel])
            abs_steer_max_deg = round(abs(steer_max * 180 / np.pi), 2)
        else:
            abs_steer_max_deg = np.nan

        kpi_table.at[row_idx, "absSteerMaxDeg"] = abs_steer_max_deg
        kpi_table.at[row_idx, "isSteerHigh"] = (
            abs_steer_max_deg > steer_ang_th if np.isfinite(abs_steer_max_deg) else False
        )

        # --- Step 5: Compute steering rate metrics
        segment_rate = steer_rate[start_idx:]
        if len(segment_rate) > 0:
            idx_rel_rate = int(np.argmax(np.abs(segment_rate)))
            steer_rate_max = float(segment_rate[idx_rel_rate])
            abs_steer_rate_max_deg = round(abs(steer_rate_max * 180 / np.pi), 2)
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
