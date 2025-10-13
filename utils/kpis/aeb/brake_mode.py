import numpy as np
import pandas as pd
import warnings

def brake_mode(mdf, kpi_table, row_idx, aeb_start_idx, pb_tgt_decel, fb_tgt_decel, tgt_tol):
    """
    Determine if PB and FB are activated during AEB event.
    Updates kpi_table in-place.

    Parameters
    ----------
    mdf : SignalMDF (or MDF wrapper)
        Must provide .aebTargetDecel and .time arrays.
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in KPI table corresponding to this file.
    aeb_start_idx : int
        Index of AEB request event.
    pb_tgt_decel : float
        Threshold value for PB activation (m/s²).
    fb_tgt_decel : float
        Threshold value for FB activation (m/s²).
    tgt_tol : float
        Tolerance when matching target decel values.
    """
    try:
        target_decel = np.asarray(mdf.aebTargetDecel)
        time = np.asarray(mdf.time)
    except AttributeError:
        warnings.warn("⚠️ Missing required signals 'aebTargetDecel' or 'time'")
        return

    if aeb_start_idx is None or aeb_start_idx >= len(time):
        warnings.warn("⚠️ Invalid AEB start index")
        return

    aeb_end_req = len(time) - 1  # last index

    # Ensure required columns exist
    for col, default, dtype in [
        ("pbDur", np.nan, "float"),
        ("fbDur", np.nan, "float"),
        ("isPBOn", False, "bool"),
        ("isFBOn", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    # Segment from AEB start to end
    segment = target_decel[aeb_start_idx:aeb_end_req + 1]

    # Find PB / FB candidate indices
    pb_idx = np.where(np.abs(segment - pb_tgt_decel) <= tgt_tol)[0]
    fb_idx = np.where(np.abs(segment - fb_tgt_decel) <= tgt_tol)[0]

    is_pb_on = len(pb_idx) > 0
    is_fb_on = len(fb_idx) > 0

    # PB duration
    if is_pb_on:
        pb_start = aeb_start_idx + pb_idx[0]
        pb_end   = aeb_start_idx + pb_idx[-1]
        pb_dur   = time[pb_end] - time[pb_start]
        kpi_table.at[row_idx, "pbDur"] = round(float(pb_dur), 3) if np.isfinite(pb_dur) else 0.0
    else:
        kpi_table.at[row_idx, "pbDur"] = 0.0

    # FB duration
    if is_fb_on:
        fb_start = aeb_start_idx + fb_idx[0]
        fb_end   = aeb_start_idx + fb_idx[-1]
        fb_dur   = time[fb_end] - time[fb_start]
        kpi_table.at[row_idx, "fbDur"] = round(float(fb_dur), 3) if np.isfinite(fb_dur) else 0.0
    else:
        kpi_table.at[row_idx, "fbDur"] = 0.0

    # Flags
    kpi_table.at[row_idx, "isPBOn"] = is_pb_on
    kpi_table.at[row_idx, "isFBOn"] = is_fb_on
