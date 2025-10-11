import numpy as np
import pandas as pd

def yaw_rate(mdf, kpi_table, row_idx, aeb_start_idx, yaw_rate_susp_th, time_idx_offset):
    """
    KPI Yaw Rate Analysis during an AEB event.
    Updates kpi_table in place.

    Parameters
    ----------
    mdf : SignalMDF (or similar wrapper)
        Must provide .yawRate (rad/s).
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    yaw_rate_susp_th : float
        Threshold for yaw rate suspension in degrees/sec.
    time_idx_offset : int
        Number of indices before AEB start to include in analysis.
    """
    # Ensure required columns exist
    for col, default, dtype in [
        ("absYawRateMaxDeg", np.nan, "float"),
        ("isYawRateHigh", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    try:
        yaw_rate = np.asarray(mdf.yawRate)
    except AttributeError:
        # Missing signal → set defaults
        kpi_table.at[row_idx, "absYawRateMaxDeg"] = np.nan
        kpi_table.at[row_idx, "isYawRateHigh"] = False
        return

    start_idx = max(0, aeb_start_idx - time_idx_offset)
    segment = yaw_rate[start_idx:]

    if len(segment) == 0:
        kpi_table.at[row_idx, "absYawRateMaxDeg"] = np.nan
        kpi_table.at[row_idx, "isYawRateHigh"] = False
        return

    # Max yaw rate within segment
    idx_rel = int(np.argmax(np.abs(segment)))
    yaw_rate_max = float(segment[idx_rel])
    abs_yaw_rate_max_deg = round(abs(yaw_rate_max * 180 / np.pi), 2)

    # Update table
    kpi_table.at[row_idx, "absYawRateMaxDeg"] = abs_yaw_rate_max_deg
    kpi_table.at[row_idx, "isYawRateHigh"] = bool(abs_yaw_rate_max_deg > yaw_rate_susp_th)
