import numpy as np
import pandas as pd
import warnings


class AebDistanceCalculator:
    """
    Computes AEB-related distance KPIs:
      • firstDetDist   — First non-zero longGap value
      • stableDetDist  — Distance where longGap becomes continuously non-zero
      • aebIntvDist    — longGap at AEB intervention start
      • aebStopGap     — longGap at AEB end
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent AebKpiExtractor instance.
        """
        # No calibrations or params needed; placeholder for extensibility
        self.extractor = extractor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_distance(self, mdf, kpi_table, row_idx, aeb_start_idx, aeb_end_idx):
        """
        Compute distance KPIs during AEB event.
        Updates kpi_table in place.
        """
        # --- Step 1: Extract signal
        try:
            long_gap = np.asarray(mdf.longGap)
        except AttributeError:
            warnings.warn(f"[Row {row_idx}] Missing required signal 'longGap'")
            return

        # --- Step 2: Ensure required columns exist
        for col in ["firstDetDist", "stableDetDist", "aebIntvDist", "aebStopGap"]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

        # --- Step 3: Validate end index
        if aeb_end_idx is None or aeb_end_idx >= len(long_gap):
            for col in ["firstDetDist", "stableDetDist", "aebIntvDist", "aebStopGap"]:
                kpi_table.at[row_idx, col] = np.nan
            warnings.warn(f"[Row {row_idx}] Invalid AEB end index — filled NaN.")
            return

        # --- Step 4: Analyze segment up to AEB end
        segment = long_gap[: aeb_end_idx + 1]

        # --- Step 5: First detection distance (first non-zero)
        nonzero_idx = np.flatnonzero(segment != 0)
        if len(nonzero_idx) > 0:
            first_nonzero_idx = nonzero_idx[0]
            first_det_dist = long_gap[first_nonzero_idx]
        else:
            first_det_dist = np.nan

        # --- Step 6: Stable detection distance (start of last continuous non-zero segment)
        if len(nonzero_idx) > 0:
            last_nonzero_idx = nonzero_idx[-1]
            trimmed = segment[: last_nonzero_idx + 1]
            zero_idx = np.flatnonzero(trimmed == 0)
            if len(zero_idx) == 0:
                stable_idx = first_nonzero_idx
            else:
                stable_idx = zero_idx[-1] + 1
            stable_det_dist = segment[stable_idx]
        else:
            stable_det_dist = np.nan

        # --- Step 7: AEB intervention start distance
        if aeb_start_idx is not None and aeb_start_idx < len(long_gap):
            aeb_intv_dist = long_gap[aeb_start_idx]
        else:
            aeb_intv_dist = np.nan

        # --- Step 8: AEB stop gap (distance at end)
        aeb_stop_gap = long_gap[aeb_end_idx]

        # --- Step 9: Write results to KPI table
        kpi_table.at[row_idx, "firstDetDist"]   = first_det_dist
        kpi_table.at[row_idx, "stableDetDist"]  = stable_det_dist
        kpi_table.at[row_idx, "aebIntvDist"]    = aeb_intv_dist
        kpi_table.at[row_idx, "aebStopGap"]     = aeb_stop_gap

        # --- Step 10: Debug summary print
        #print(
        #    f"📏 [Row {row_idx}] Distance KPIs:\n"
        #    f"   • First Detection   = {first_det_dist if np.isfinite(first_det_dist) else 'NaN'}\n"
        #    f"   • Stable Detection  = {stable_det_dist if np.isfinite(stable_det_dist) else 'NaN'}\n"
        #    f"   • AEB Start Dist.   = {aeb_intv_dist if np.isfinite(aeb_intv_dist) else 'NaN'}\n"
        #    f"   • AEB Stop Gap      = {aeb_stop_gap if np.isfinite(aeb_stop_gap) else 'NaN'}\n"
        #)
