import numpy as np
import pandas as pd

def lat_accel(mdf, kpi_table, row_idx, aeb_start_idx, lat_accel_th, time_idx_offset):
    """
    Compute lateral acceleration KPIs during an AEB event.
    Updates kpi_table in place.

    Parameters
    ----------
    mdf : SignalMDF (or similar wrapper)
        Must provide .latActAccelFlt (filtered lateral acceleration).
    kpi_table : pandas.DataFrame
        KPI results table (will be updated in place).
    row_idx : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    lat_accel_th : float
        Threshold for high lateral acceleration [m/s²].
    time_idx_offset : int
        Number of indices to include before the AEB start event.
    """
    try:
        lat_accel_flt = np.asarray(mdf.latActAccelFlt)
    except AttributeError:
        raise KeyError("⚠️ Missing 'latActAccelFlt' signal in MDF")

    # Ensure required columns exist
    for col, default, dtype in [
        ("absLatAccelMax", np.nan, "float"),
        ("isLatAccelHigh", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    # Slice from (aeb_start_idx - offset) to end
    start_idx = max(0, aeb_start_idx - time_idx_offset)
    segment = lat_accel_flt[start_idx:]

    if len(segment) == 0:
        kpi_table.at[row_idx, "absLatAccelMax"] = np.nan
        kpi_table.at[row_idx, "isLatAccelHigh"] = False
        return

    # Find max absolute lateral accel
    idx_rel = int(np.argmax(np.abs(segment)))
    lat_accel_max = segment[idx_rel]
    abs_lat_accel_max = abs(lat_accel_max)

    # Update table
    kpi_table.at[row_idx, "absLatAccelMax"] = float(abs_lat_accel_max)
    kpi_table.at[row_idx, "isLatAccelHigh"] = abs_lat_accel_max > lat_accel_th
