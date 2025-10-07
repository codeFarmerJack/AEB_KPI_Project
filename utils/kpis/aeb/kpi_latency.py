import numpy as np
import pandas as pd
import warnings
from utils.time_locators import detect_kneepoint  


def kpi_latency(mdf, kpi_table, row_idx, aeb_start_idx, cutoff_freq):
    """
    Compute AEB system latency KPIs.
    Updates kpi_table in place.

    Parameters
    ----------
    mdf : SignalMDF (or similar wrapper)
        Must provide .time and .longActAccel arrays.
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in kpi_table.
    aeb_start_idx : int
        Index of AEB intervention request (start).
    cutoff_freq : float
        Cutoff frequency for filtering in kneepoint detection.
    """

    # Ensure required columns exist
    for col in ["aebSysRespTime", "aebDeadTime"]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

    time = np.asarray(mdf.time)
    long_accel = np.asarray(mdf.longActAccel)

    # Validate data range (look 30 samples ahead after AEB start)
    start_idx = aeb_start_idx
    end_idx = min(aeb_start_idx + 30, len(time) - 1)
    if start_idx > end_idx:
        warnings.warn(
            f"Invalid range for kneepoint detection at row {row_idx}. "
            f"Setting aebSysRespTime and aebDeadTime to NaN."
        )
        kpi_table.at[row_idx, "aebSysRespTime"] = np.nan
        kpi_table.at[row_idx, "aebDeadTime"] = np.nan
        return

    # --- Detect kneepoint in deceleration ---
    knee_idx, knee_time, _ = detect_kneepoint(
        time=time[start_idx:end_idx + 1],
        acc=long_accel[start_idx:end_idx + 1],
        direction="negative",
        cutoff_freq=cutoff_freq,
        method="curvature",
    )

    # AEB intervention request time (start of event)
    t_request = time[aeb_start_idx]

    # System response time from kneepoint
    t_sys_resp = knee_time if np.isfinite(knee_time) else np.nan

    # Dead time = system response - request
    dead_time_value = float(t_sys_resp - t_request) if np.isfinite(t_sys_resp) and np.isfinite(t_request) else np.nan

    # Save into table
    kpi_table.at[row_idx, "aebSysRespTime"] = round(float(t_sys_resp), 2) if np.isfinite(t_sys_resp) else np.nan
    kpi_table.at[row_idx, "aebDeadTime"] = round(dead_time_value, 2) if np.isfinite(dead_time_value) else np.nan