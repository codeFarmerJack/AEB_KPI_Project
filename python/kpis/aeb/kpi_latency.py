import numpy as np
import pandas as pd
import warnings
from utils.time_locators import detect_kneepoint_v4  # assuming you placed it there

def kpi_latency(obj, i, aeb_start_idx):
    """
    Compute AEB system latency KPIs.
    Updates obj.kpi_table in place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict with arrays {time, longActAccel}
        - CUTOFF_FREQ : float
    i : int
        Row index in kpi_table.
    aeb_start_idx : int
        Index of AEB request event.
    """
    kpi_table = obj.kpi_table
    signals = obj.signal_mat_chunk
    cutoff_freq = obj.CUTOFF_FREQ

    # Ensure required columns exist
    for col in ["m1IntvSysResp", "m1DeadTime"]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

    # Validate data range
    start_idx = aeb_start_idx
    end_idx = min(aeb_start_idx + 30, len(signals["time"]) - 1)
    if start_idx > end_idx:
        warnings.warn(
            f"Invalid range for kneepoint detection at index {i}. "
            f"Setting m1IntvSysResp and m1DeadTime to NaN."
        )
        kpi_table.at[i, "m1IntvSysResp"] = np.nan
        kpi_table.at[i, "m1DeadTime"] = np.nan
        return

    # Detect kneepoint
    knee_idx, _, _ = detect_kneepoint_v4(
        time=signals["time"][start_idx:end_idx + 1],
        acc=signals["longActAccel"][start_idx:end_idx + 1],
        direction="negative",
        cutoff_freq=cutoff_freq,
        method="curvature",
    )

    # Compute M0 and M1
    M0 = signals["time"][aeb_start_idx]
    M1_idx = min(aeb_start_idx + max(0, knee_idx), len(signals["time"]) - 1)
    M1 = signals["time"][M1_idx]

    # Assign m1IntvSysResp
    try:
        m1_value = float(M1)  # assumes numeric time in seconds
    except Exception:
        m1_value = np.nan
    if np.isfinite(m1_value):
        kpi_table.at[i, "m1IntvSysResp"] = round(m1_value, 2)
    else:
        warnings.warn(f"Invalid M1 value for file index {i}: {M1}. Setting NaN.")
        kpi_table.at[i, "m1IntvSysResp"] = np.nan

    # Dead time (latency)
    try:
        dead_time_value = float(M1 - M0)
    except Exception:
        dead_time_value = np.nan
    if np.isfinite(dead_time_value):
        kpi_table.at[i, "m1DeadTime"] = round(dead_time_value, 2)
    else:
        warnings.warn(f"Invalid deadTime for file index {i}. Setting NaN.")
        kpi_table.at[i, "m1DeadTime"] = np.nan

    # Optional: return row as dict for debugging
    return kpi_table.loc[i, ["m1IntvSysResp", "m1DeadTime"]].to_dict()
