import numpy as np
import pandas as pd

def kpi_lat_accel(obj, i, aeb_start_idx, lat_accel_th):
    """
    Compute lateral acceleration KPIs during an AEB event.
    Updates obj.kpi_table in place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict-like with array "latActAccelFlt"
        - TIME_IDX_OFFSET : int
    i : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    lat_accel_th : float
        Threshold for high lateral acceleration [m/s²].
    """
    kpi_table = obj.kpi_table
    signals = obj.signal_mat_chunk
    offset = obj.TIME_IDX_OFFSET

    # Ensure required columns exist
    for col, default, dtype in [
        ("latAccelMax", np.nan, "float"),
        ("absLatAccelMax", np.nan, "float"),
        ("isLatAccelHigh", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    # Slice from AEB start - offset to end
    segment = signals["latActAccelFlt"][aeb_start_idx - offset :]

    # Find max absolute lateral accel
    idx_rel = int(np.argmax(np.abs(segment)))
    lat_accel_max = segment[idx_rel]
    abs_lat_accel_max = abs(lat_accel_max)

    # Update table
    kpi_table.at[i, "latAccelMax"] = float(lat_accel_max)
    kpi_table.at[i, "absLatAccelMax"] = float(abs_lat_accel_max)
    kpi_table.at[i, "isLatAccelHigh"] = abs_lat_accel_max > lat_accel_th
