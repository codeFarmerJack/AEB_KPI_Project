import numpy as np
import pandas as pd
import warnings


class LsaebDistanceCalculator:
    """
    Computes LSAEB-related distance KPIs:
      • lsaebIntvLongDist  — Longitudinal distance at LSAEB intervention start
      • lsaebIntvLatDist   — Lateral distance at LSAEB intervention start
      • lsaebStopLongDist  — Longitudinal distance when vehicle stopped
      • lsaebStopLatDist   — Lateral distance when vehicle stopped
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent LsaebKpiExtractor instance.
        """
        self.extractor = extractor

    # ------------------------------------------------------------------
    def compute_distance(self, mdf, kpi_table, row_idx, lsaeb_start_idx, lsaeb_end_idx):
        """
        Compute distance KPIs for LSAEB event.
        Updates kpi_table in place.
        """

        # --- Step 1: Extract signals
        try:
            long_dist = np.asarray(mdf.cpmLongDist)
            lat_dist = np.asarray(mdf.cpmLatDist)
        except AttributeError:
            warnings.warn(f"[Row {row_idx}] Missing required signals 'cpmLongDist' or 'cpmLatDist'")
            return

        # --- Step 2: Ensure required columns exist
        for col in ["lsaebIntvLongDist", "lsaebIntvLatDist", "lsaebStopLongDist", "lsaebStopLatDist"]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

        # --- Step 3: Validate event indices
        n = len(long_dist)
        if n == 0:
            warnings.warn(f"[Row {row_idx}] Empty distance signals.")
            return

        if lsaeb_start_idx is None or lsaeb_start_idx >= n:
            warnings.warn(f"[Row {row_idx}] Invalid LSAEB start index — filled NaN.")
            lsaeb_start_idx = None

        if lsaeb_end_idx is None or lsaeb_end_idx >= n:
            warnings.warn(f"[Row {row_idx}] Invalid LSAEB end index — filled NaN.")
            lsaeb_end_idx = None

        # --- Step 4: LSAEB intervention distances
        if lsaeb_start_idx is not None:
            intv_long_dist = long_dist[lsaeb_start_idx]
            intv_lat_dist = lat_dist[lsaeb_start_idx]
        else:
            intv_long_dist = np.nan
            intv_lat_dist = np.nan

        # --- Step 5: LSAEB stop gaps (at end)
        if lsaeb_end_idx is not None:
            stop_long_gap = long_dist[lsaeb_end_idx]
            stop_lat_gap = lat_dist[lsaeb_end_idx]
        else:
            stop_long_gap = np.nan
            stop_lat_gap = np.nan

        # --- Step 6: Write results to KPI table
        kpi_table.at[row_idx, "lsaebIntvLongDist"]  = intv_long_dist
        kpi_table.at[row_idx, "lsaebIntvLatDist"]   = intv_lat_dist
        kpi_table.at[row_idx, "lsaebStopLongDist"]  = stop_long_gap
        kpi_table.at[row_idx, "lsaebStopLatDist"]   = stop_lat_gap

        # --- Step 7: Optional debug summary
        # print(
        #     f"📏 [Row {row_idx}] LSAEB Distance KPIs:\n"
        #     f"   • Intv LongDist  = {intv_long_dist if np.isfinite(intv_long_dist) else 'NaN'}\n"
        #     f"   • Intv LatDist   = {intv_lat_dist if np.isfinite(intv_lat_dist) else 'NaN'}\n"
        #     f"   • Stop LongGap   = {stop_long_gap if np.isfinite(stop_long_gap) else 'NaN'}\n"
        #     f"   • Stop LatGap    = {stop_lat_gap if np.isfinite(stop_lat_gap) else 'NaN'}\n"
        # )
