import numpy as np
import pandas as pd
import warnings
from utils.event_detector.decel import detect_decel_onset


def latency(mdf, kpi_table, row_idx, aeb_start_idx, neg_thd, latency_window_samples):
    """
    Compute AEB system latency KPIs.
    Updates kpi_table in place.

    Parameters
    ----------
    mdf : SignalMDF
        Must provide .time and .longActAccelFlt arrays.
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in kpi_table.
    aeb_start_idx : int
        Index of AEB intervention request (start).
    neg_thd : float, optional
        Negative jerk threshold (m/s³) for decel onset detection.
    window_samples : int, optional
        Number of samples to analyze after AEB start for latency detection.
    """

    # Ensure required columns exist
    for col in ["aebSysRespTime", "aebDeadTime"]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

    time            = np.asarray(mdf.time)
    long_accel_flt  = np.asarray(mdf.longActAccelFlt)

    # Validate data range (look 30 samples ahead after AEB start)
    start_idx = aeb_start_idx
    end_idx = min(aeb_start_idx + latency_window_samples, len(time) - 1)
    if start_idx > end_idx:
        warnings.warn(
            f"Invalid range for kneepoint detection at row {row_idx}. "
            f"Setting aebSysRespTime and aebDeadTime to NaN."
        )
        kpi_table.at[row_idx, "aebSysRespTime"] = np.nan
        kpi_table.at[row_idx, "aebDeadTime"] = np.nan
        return

    jerk = np.gradient(long_accel_flt[start_idx:end_idx + 1], time[start_idx:end_idx + 1])

    resp_idx_rel = detect_decel_onset(jerk, neg_thd)
    if resp_idx_rel is not None:
        resp_idx_abs = start_idx + resp_idx_rel
        t_sys_resp = time[resp_idx_abs]
    else:
        resp_idx_abs = None
        t_sys_resp = np.nan

    # AEB intervention request time (start of event)
    t_request = time[aeb_start_idx]

    # Dead time = system response - request
    dead_time_value = float(t_sys_resp - t_request) if np.isfinite(t_sys_resp) and np.isfinite(t_request) else np.nan

    # Save into table
    kpi_table.at[row_idx, "aebSysRespTime"] = round(float(t_sys_resp), 3) if np.isfinite(t_sys_resp) else np.nan
    kpi_table.at[row_idx, "aebDeadTime"] = round(dead_time_value, 3) if np.isfinite(dead_time_value) else np.nan