import numpy as np
import pandas as pd
import warnings


class AebYawRateCalculator:
    """
    Computes yaw rate KPIs during an AEB event.

    KPIs extracted:
      • absYawRateMaxDeg - Maximum absolute yaw rate (°/s)
      • isYawRateHigh    - True if absYawRateMaxDeg > yaw_rate_susp_th
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent AebKpiExtractor instance.
        """
        self.time_idx_offset = extractor.time_idx_offset  # e.g. ~300 samples (~3s)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_yaw_rate(self, mdf, kpi_table, row_idx, aeb_start_idx, yaw_rate_susp_th):
        """
        Compute yaw rate KPIs during an AEB event.
        Updates kpi_table in place.
        """
        # --- Step 1: Ensure required columns exist
        for col, default, dtype in [
            ("absYawRateMaxDeg", np.nan, "float"),
            ("isYawRateHigh", False, "bool"),
        ]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

        # --- Step 2: Extract signal
        try:
            yaw_rate = np.asarray(mdf.yawRate)
        except AttributeError:
            warnings.warn(f"[Row {row_idx}] Missing required signal 'yawRate'")
            self._fill_defaults(kpi_table, row_idx)
            return

        # --- Step 3: Validate start index
        if aeb_start_idx is None or aeb_start_idx >= len(yaw_rate):
            warnings.warn(f"[Row {row_idx}] Invalid AEB start index")
            self._fill_defaults(kpi_table, row_idx)
            return

        start_idx = max(0, aeb_start_idx - self.time_idx_offset)
        segment = yaw_rate[start_idx:]

        if len(segment) == 0:
            self._fill_defaults(kpi_table, row_idx)
            return

        # --- Step 4: Compute maximum yaw rate in segment
        idx_rel = int(np.argmax(np.abs(segment)))
        yaw_rate_max = float(segment[idx_rel])
        abs_yaw_rate_max_deg = round(abs(yaw_rate_max * 180 / np.pi), 2)

        # --- Step 5: Write results
        kpi_table.at[row_idx, "absYawRateMaxDeg"] = abs_yaw_rate_max_deg
        kpi_table.at[row_idx, "isYawRateHigh"] = (
            abs_yaw_rate_max_deg > yaw_rate_susp_th if np.isfinite(abs_yaw_rate_max_deg) else False
        )

        # --- Step 6: Debug print
        #print(
        #    f"🌀 [Row {row_idx}] Yaw Rate KPIs:\n"
        #    f"   • absYawRateMaxDeg = {abs_yaw_rate_max_deg if np.isfinite(abs_yaw_rate_max_deg) else 'NaN'}°/s\n"
        #    f"   • Threshold        = {yaw_rate_susp_th:.2f}°/s → High = "
        #    f"{kpi_table.at[row_idx, 'isYawRateHigh']}\n"
        #)

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _fill_defaults(self, kpi_table, row_idx):
        """Fill default values when signal or index is invalid."""
        kpi_table.at[row_idx, "absYawRateMaxDeg"] = np.nan
        kpi_table.at[row_idx, "isYawRateHigh"] = False
