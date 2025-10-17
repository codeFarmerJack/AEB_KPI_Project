import numpy as np
import pandas as pd
import warnings


class AebLatAccelCalculator:
    """
    Computes lateral acceleration KPIs during an AEB event.

    KPIs extracted:
      • absLatAccelMax - Maximum absolute lateral acceleration (m/s²)
      • isLatAccelHigh - True if absLatAccelMax > lat_accel_th
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent AebKpiExtractor instance.
        """
        self.time_idx_offset = extractor.time_idx_offset

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_lat_accel(self, mdf, kpi_table, row_idx, aeb_start_idx, lat_accel_th):
        """
        Compute lateral acceleration KPIs during an AEB event.
        Updates kpi_table in place.
        """
        # --- Step 1: Extract lateral acceleration signal
        try:
            lat_accel_flt = np.asarray(mdf.latActAccelFlt)
        except AttributeError:
            warnings.warn(f"[Row {row_idx}] Missing signal 'latActAccelFlt'")
            self._fill_defaults(kpi_table, row_idx)
            return

        # --- Step 2: Ensure KPI columns exist
        for col, default, dtype in [
            ("absLatAccelMax", np.nan, "float"),
            ("isLatAccelHigh", False, "bool"),
        ]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

        # --- Step 3: Validate index and slice window
        if aeb_start_idx is None or aeb_start_idx >= len(lat_accel_flt):
            warnings.warn(f"[Row {row_idx}] Invalid AEB start index")
            self._fill_defaults(kpi_table, row_idx)
            return

        start_idx = max(0, aeb_start_idx - self.time_idx_offset)
        segment = lat_accel_flt[start_idx:]

        if len(segment) == 0:
            self._fill_defaults(kpi_table, row_idx)
            return

        # --- Step 4: Find maximum absolute lateral acceleration
        idx_rel           = int(np.argmax(np.abs(segment)))
        lat_accel_max     = segment[idx_rel]
        abs_lat_accel_max = abs(lat_accel_max)

        # --- Step 5: Write to KPI table
        kpi_table.at[row_idx, "absLatAccelMax"] = float(abs_lat_accel_max)
        kpi_table.at[row_idx, "isLatAccelHigh"] = abs_lat_accel_max > lat_accel_th

        # --- Step 6: Debug print
        #print(
        #    f"🌐 [Row {row_idx}] Lateral Acceleration KPIs:\n"
        #    f"   • absLatAccelMax = {abs_lat_accel_max:.3f} m/s²\n"
        #    f"   • Threshold      = {lat_accel_th:.3f} m/s² → High = {abs_lat_accel_max > lat_accel_th}\n"
        #)

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _fill_defaults(self, kpi_table, row_idx):
        """Fill default values when signal or indices are invalid."""
        kpi_table.at[row_idx, "absLatAccelMax"] = np.nan
        kpi_table.at[row_idx, "isLatAccelHigh"] = False
