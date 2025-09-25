import numpy as np
import pandas as pd

def kpi_yaw_rate(obj, i, aeb_start_idx, yaw_rate_susp_th):
    """
    KPI Yaw Rate Analysis during an AEB event.
    Updates obj.kpi_table in place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict with array "yawRate" (rad/s)
        - TIME_IDX_OFFSET : int
    i : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    yaw_rate_susp_th : float
        Threshold for yaw rate suspension in degrees/sec.
    """
    kpi_table = obj.kpi_table
    signals = obj.signal_mat_chunk
    offset = obj.TIME_IDX_OFFSET

    # Ensure required columns exist
    for col, default, dtype in [
        ("yawRateMax", np.nan, "float"),
        ("absYawRateMaxDeg", np.nan, "float"),
        ("isYawRateHigh", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    # Slice yaw rate signal
    segment = signals["yawRate"][aeb_start_idx - offset :]
    idx_rel = int(np.argmax(np.abs(segment)))
    yaw_rate_max = segment[idx_rel]
    abs_yaw_rate_max_deg = round(abs(yaw_rate_max * 180 / np.pi), 2)

    # Update table
    kpi_table.at[i, "yawRateMax"] = float(yaw_rate_max)
    kpi_table.at[i, "absYawRateMaxDeg"] = abs_yaw_rate_max_deg
    kpi_table.at[i, "isYawRateHigh"] = abs_yaw_rate_max_deg > yaw_rate_susp_th
