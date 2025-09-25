import numpy as np
import pandas as pd

def kpi_distance(obj, i, aeb_start_idx, aeb_end_idx):
    """
    Compute distance KPIs during AEB event.
    Updates obj.kpi_table in place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict-like with array "longGap"
    i : int
        Index of the file in kpi_table.
    aeb_start_idx : int
        Index of AEB request event.
    aeb_end_idx : int
        Index of AEB end event.
    """
    kpi_table = obj.kpi_table
    long_gap = np.asarray(obj.signal_mat_chunk["longGap"])

    # Ensure required columns exist
    for col in ["firstDetDist", "stableDetDist", "aebIntvDist", "aebStopGap"]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

    # Consider segment up to AEB end
    segment = long_gap[: aeb_end_idx + 1]

    # First detection distance (first non-zero)
    nonzero_idx = np.flatnonzero(segment != 0)
    if len(nonzero_idx) > 0:
        first_nonzero_idx = nonzero_idx[0]
        kpi_table.at[i, "firstDetDist"] = long_gap[first_nonzero_idx]
    else:
        kpi_table.at[i, "firstDetDist"] = np.nan

    # Stable detection distance (start of last continuous non-zero segment)
    if len(nonzero_idx) > 0:
        last_nonzero_idx = nonzero_idx[-1]
        trimmed = segment[: last_nonzero_idx + 1]
        zero_idx = np.flatnonzero(trimmed == 0)
        if len(zero_idx) == 0:
            stable_idx = first_nonzero_idx
        else:
            stable_idx = zero_idx[-1] + 1
        kpi_table.at[i, "stableDetDist"] = segment[stable_idx]
    else:
        kpi_table.at[i, "stableDetDist"] = np.nan

    # AEB intervention distance at start and end
    kpi_table.at[i, "aebIntvDist"] = long_gap[aeb_start_idx]
    kpi_table.at[i, "aebStopGap"] = long_gap[aeb_end_idx]
