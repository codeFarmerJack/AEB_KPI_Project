import numpy as np
import pandas as pd
import warnings

def brake_jerk(mdf, kpi_table, row_idx,
               window_s: float = 1.0,
               jerk_thresh: float | None = None,
               mad_scale: float = 4.0):
    """
    Compute and record brake jerk KPIs directly into kpi_table.

    Parameters
    ----------
    mdf : SignalMDF
        Must provide .time, .vehAccel, and .fcwRequest signals.
    kpi_table : pandas.DataFrame
        KPI table to update in place.
    row_idx : int
        Row index in KPI table corresponding to this file.
    window_s : float, optional
        Duration after FCW=3 rising edge to search (default 1 s).
    jerk_thresh : float or None, optional
        Fixed jerk threshold (m/s³). If None, uses adaptive MAD-based threshold.
    mad_scale : float, optional
        Scaling factor for adaptive threshold (default 4×MAD).

    Notes
    -----
    - Creates columns if missing: brakeJerkDur, brakeJerkStart, brakeJerkEnd,
      brakeJerkThd, brakeJerkMax, brakeAccelMax
    """

    # --- Extract signals ---
    try:
        time        = mdf.time
        accel       = mdf.longAccelFlt
        fcw_request = mdf.fcwRequest
    except AttributeError:
        warnings.warn("⚠️ Missing required signals (time, longAccelFlt, fcwRequest).")
        return

    if len(time) < 3 or np.any(np.diff(time) <= 0):
        warnings.warn("⚠️ Invalid or unsorted time vector.")
        return

    # Ensure KPI columns exist
    for col in [
        "brakeJerkDur", "brakeJerkStart", "brakeJerkEnd",
        "brakeJerkThd", "brakeJerkMax", "brakeAccelMax"
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = np.nan

    # --- Compute jerk (first derivative of accel) ---
    jerk = np.gradient(accel, time)

    # --- Detect FCW rising edges (→3) ---
    edges = np.where((fcw_request[:-1] < 3) & (fcw_request[1:] >= 3))[0]
    if len(edges) == 0:
        warnings.warn("⚠️ No FCW rising edges detected.")
        return

    t0 = time[edges[0] + 1]
    mask = (time >= t0) & (time <= t0 + window_s)
    if not np.any(mask):
        warnings.warn("⚠️ No valid jerk window after FCW rise.")
        return

    tw = time[mask]
    jw = jerk[mask]

    # --- Adaptive threshold if needed ---
    if jerk_thresh is None:
        med = np.median(jw)
        mad = np.median(np.abs(jw - med)) + 1e-12
        thr = max(0.5, mad_scale * 1.4826 * mad)
    else:
        thr = float(jerk_thresh)

    # --- Find bowl-shaped jerk region ---
    neg_idx = np.where(jw < -thr)[0]
    pos_idx = np.where(jw > thr)[0]
    if len(neg_idx) == 0 or len(pos_idx) == 0:
        warnings.warn("⚠️ No complete jerk bowl found.")
        return

    i0 = neg_idx[0]
    later_pos = pos_idx[pos_idx > i0]
    if len(later_pos) == 0:
        warnings.warn("⚠️ Missing positive recovery in jerk curve.")
        return
    i1 = later_pos[0]

    dur = tw[i1] - tw[i0]
    max_jerk = np.max(np.abs(jw))
    max_accel = np.max(accel[mask]) if np.any(mask) else np.nan

    # --- Write results to KPI table ---
    kpi_table.at[row_idx, "brakeJerkDur"]   = round(float(dur), 3)
    kpi_table.at[row_idx, "brakeJerkStart"] = float(tw[i0])
    kpi_table.at[row_idx, "brakeJerkEnd"]   = float(tw[i1])
    kpi_table.at[row_idx, "brakeJerkThd"]   = float(thr)
    kpi_table.at[row_idx, "brakeJerkMax"]   = float(max_jerk)
    kpi_table.at[row_idx, "brakeAccelMax"]  = float(max_accel)

    print(
        f"   ✅ brakeJerkDur={dur:.3f}s | "
        f"Start={tw[i0]:.3f}s | End={tw[i1]:.3f}s | Thd={thr:.3f}"
    )
