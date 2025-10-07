import numpy as np
import pandas as pd

def kpi_distance(mdf, kpi_table, row_idx, aeb_start_idx, aeb_end_idx):
    """
    Compute distance KPIs during AEB event.
    Updates kpi_table in place.

    Parameters
    ----------
    mdf : SignalMDF (or MDF subclass/wrapper)
        Must provide .longGap as a numpy array.
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in KPI table corresponding to this file.
    aeb_start_idx : int
        Index of AEB request event.
    aeb_end_idx : int
        Index of AEB end event.
    """
    # Extract signal
    try:
        long_gap = np.asarray(mdf.longGap)
    except AttributeError:
        raise RuntimeError("SignalMDF missing required channel 'longGap'")

    # Ensure required columns exist
    for col in ["firstDetDist", "stableDetDist", "aebIntvDist", "aebStopGap"]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

    # If end idx is invalid → fill NaNs
    if aeb_end_idx is None or aeb_end_idx >= len(long_gap):
        kpi_table.at[row_idx, "firstDetDist"]  = np.nan
        kpi_table.at[row_idx, "stableDetDist"] = np.nan
        kpi_table.at[row_idx, "aebIntvDist"]   = np.nan
        kpi_table.at[row_idx, "aebStopGap"]    = np.nan
        return

    # Consider segment up to AEB end
    segment = long_gap[: aeb_end_idx + 1]

    # First detection distance (first non-zero)
    nonzero_idx = np.flatnonzero(segment != 0)
    if len(nonzero_idx) > 0:
        first_nonzero_idx = nonzero_idx[0]
        kpi_table.at[row_idx, "firstDetDist"] = long_gap[first_nonzero_idx]
    else:
        kpi_table.at[row_idx, "firstDetDist"] = np.nan

    # Stable detection distance (start of last continuous non-zero segment)
    if len(nonzero_idx) > 0:
        last_nonzero_idx = nonzero_idx[-1]
        trimmed = segment[: last_nonzero_idx + 1]
        zero_idx = np.flatnonzero(trimmed == 0)
        if len(zero_idx) == 0:
            stable_idx = first_nonzero_idx
        else:
            stable_idx = zero_idx[-1] + 1
        kpi_table.at[row_idx, "stableDetDist"] = segment[stable_idx]
    else:
        kpi_table.at[row_idx, "stableDetDist"] = np.nan

    # AEB intervention distance at start and end
    if aeb_start_idx is not None and aeb_start_idx < len(long_gap):
        kpi_table.at[row_idx, "aebIntvDist"] = long_gap[aeb_start_idx]
    else:
        kpi_table.at[row_idx, "aebIntvDist"] = np.nan

    kpi_table.at[row_idx, "aebStopGap"] = long_gap[aeb_end_idx]
