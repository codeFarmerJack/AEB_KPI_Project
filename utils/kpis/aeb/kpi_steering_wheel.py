import numpy as np
import pandas as pd

def kpi_steering_wheel(mdf, kpi_table, row_idx, aeb_start_idx, steer_ang_th, steer_ang_rate_th, time_idx_offset):
    """
    Steering wheel analysis during an AEB event.
    Updates kpi_table in place.

    Parameters
    ----------
    mdf : SignalMDF (or similar wrapper)
        Must provide .steerWheelAngle and .steerWheelAngleSpeed arrays.
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    steer_ang_th : float
        Threshold for steering angle in degrees.
    steer_ang_rate_th : float
        Threshold for steering angle rate in degrees/sec.
    time_idx_offset : int
        Number of indices before AEB start to include in the analysis.
    """
    # Ensure required columns exist
    for col, default, dtype in [
        ("absSteerMaxDeg", np.nan, "float"),
        ("isSteerHigh", False, "bool"),
        ("absSteerRateMaxDeg", np.nan, "float"),
        ("isSteerAngRateHigh", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    steer_angle = np.asarray(mdf.steerWheelAngle)
    steer_rate  = np.asarray(mdf.steerWheelAngleSpeed)

    start_idx = max(0, aeb_start_idx - time_idx_offset)

    # --- Steering angle ---
    segment_angle = steer_angle[start_idx:]
    if len(segment_angle) > 0:
        idx_rel = int(np.argmax(np.abs(segment_angle)))
        steer_max = float(segment_angle[idx_rel])
        abs_steer_max_deg = round(abs(steer_max * 180 / np.pi), 2)
    else:
        steer_max = np.nan
        abs_steer_max_deg = np.nan

    kpi_table.at[row_idx, "absSteerMaxDeg"] = abs_steer_max_deg
    kpi_table.at[row_idx, "isSteerHigh"] = abs_steer_max_deg > steer_ang_th if np.isfinite(abs_steer_max_deg) else False

    # --- Steering angle rate ---
    segment_rate = steer_rate[start_idx:]
    if len(segment_rate) > 0:
        idx_rel_rate = int(np.argmax(np.abs(segment_rate)))
        steer_rate_max = float(segment_rate[idx_rel_rate])
        abs_steer_rate_max_deg = round(abs(steer_rate_max * 180 / np.pi), 2)
    else:
        steer_rate_max = np.nan
        abs_steer_rate_max_deg = np.nan

    kpi_table.at[row_idx, "absSteerRateMaxDeg"] = abs_steer_rate_max_deg
    kpi_table.at[row_idx, "isSteerAngRateHigh"] = abs_steer_rate_max_deg > steer_ang_rate_th if np.isfinite(abs_steer_rate_max_deg) else False
