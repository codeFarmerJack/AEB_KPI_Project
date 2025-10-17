import numpy as np
import pandas as pd
import warnings


class AebThrottleCalculator:
    """
    Computes throttle-related KPIs during an AEB event.

    KPIs extracted:
      • pedalPosAtStart   – Pedal position at start of AEB intervention
      • pedalPosMax       – Maximum pedal position during AEB event
      • pedalPosInc       – Increment (Max - Start)
      • isPedalPosIncHigh – True if pedalPosInc exceeds threshold
      • isPedalOnAtStrt   – True if pedal was pressed at AEB start

    Constructed from an AebKpiExtractor instance:

        self.throttle_calc = AebThrottleCalculator(self)

    Called within the KPI loop:

        self.throttle_calc.compute_throttle(mdf, self.kpi_table, i, aeb_start_idx)
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """Initialize from parent AebKpiExtractor instance."""
        pass  # no attributes needed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_throttle(self, mdf, kpi_table, row_idx, aeb_start_idx, pedal_pos_inc_th):
        """
        Compute throttle KPIs during an AEB event.
        Updates kpi_table in place.
        """
        # --- Step 1: Ensure required columns exist
        for col, default, dtype in [
            ("pedalPosAtStart", np.nan, "float"),
            ("pedalPosMax", np.nan, "float"),
            ("pedalPosInc", np.nan, "float"),
            ("isPedalPosIncHigh", False, "bool"),
            ("isPedalOnAtStrt", False, "bool"),
        ]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

        # --- Step 2: Extract throttle signal
        try:
            throttle = np.asarray(mdf.throttleValue)
        except AttributeError:
            warnings.warn(f"[Row {row_idx}] Missing required signal 'throttleValue'")
            self._fill_defaults(kpi_table, row_idx)
            return

        # --- Step 3: Validate AEB start index
        if aeb_start_idx is None or aeb_start_idx < 0 or aeb_start_idx >= len(throttle):
            warnings.warn(f"[Row {row_idx}] Invalid AEB start index")
            self._fill_defaults(kpi_table, row_idx)
            return

        # --- Step 4: Compute pedal position at start
        pedal_start = float(throttle[aeb_start_idx])
        kpi_table.at[row_idx, "pedalPosAtStart"] = pedal_start
        kpi_table.at[row_idx, "isPedalOnAtStrt"] = (pedal_start != 0)

        # --- Step 5: Compute maximum pedal position after AEB start
        throttle_range = throttle[aeb_start_idx:]
        pedal_max = float(np.max(throttle_range)) if len(throttle_range) else np.nan
        kpi_table.at[row_idx, "pedalPosMax"] = pedal_max

        # --- Step 6: Compute increment
        if np.isfinite(pedal_max) and np.isfinite(pedal_start):
            pedal_inc = pedal_max - pedal_start
        else:
            pedal_inc = np.nan
        kpi_table.at[row_idx, "pedalPosInc"] = pedal_inc

        # --- Step 7: Threshold check
        if np.isfinite(pedal_inc):
            is_high = pedal_inc > pedal_pos_inc_th
        else:
            is_high = False
        kpi_table.at[row_idx, "isPedalPosIncHigh"] = is_high

        # --- Step 8: Debug print (consistent with other KPI calculators)
        print(
            f"⚙️ [Row {row_idx}] Throttle KPIs:\n"
            f"   • Pedal Start      = {pedal_start:.3f}\n"
            f"   • Pedal Max        = {pedal_max:.3f}\n"
            f"   • Pedal Increment  = {pedal_inc:.3f}\n"
            f"   • Threshold ({pedal_pos_inc_th}) → High = {is_high}\n"
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _fill_defaults(self, kpi_table, row_idx):
        """Fill default values when signal or index is invalid."""
        kpi_table.at[row_idx, "pedalPosAtStart"]    = np.nan
        kpi_table.at[row_idx, "pedalPosMax"]        = np.nan
        kpi_table.at[row_idx, "pedalPosInc"]        = np.nan
        kpi_table.at[row_idx, "isPedalPosIncHigh"]  = False
        kpi_table.at[row_idx, "isPedalOnAtStrt"]    = False
