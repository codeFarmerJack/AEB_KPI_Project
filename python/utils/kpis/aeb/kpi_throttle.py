import numpy as np
import pandas as pd

def kpi_throttle(obj, i, aeb_start_idx, pedal_pos_inc_th):
    """
    Throttle pedal analysis during an AEB event.
    Updates obj.kpi_table in place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict with array "throttleValue"
    i : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    pedal_pos_inc_th : float
        Threshold for pedal position increase.
    """
    kpi_table = obj.kpi_table
    signals = obj.signal_mat_chunk

    # Ensure required columns exist
    for col, default, dtype in [
        ("pedalStart", np.nan, "float"),
        ("pedalMax", np.nan, "float"),
        ("pedalInc", np.nan, "float"),
        ("isPedalHigh", False, "bool"),
        ("isPedalOnAtStrt", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    # Validate presence of throttle signal
    if "throttleValue" not in signals:
        kpi_table.at[i, "pedalStart"] = np.nan
        kpi_table.at[i, "pedalMax"] = np.nan
        kpi_table.at[i, "pedalInc"] = np.nan
        kpi_table.at[i, "isPedalHigh"] = False
        kpi_table.at[i, "isPedalOnAtStrt"] = False
        return

    throttle = np.asarray(signals["throttleValue"])

    # Validate aeb_start_idx
    if (
        aeb_start_idx is None
        or aeb_start_idx < 0
        or aeb_start_idx >= len(throttle)
    ):
        kpi_table.at[i, "pedalStart"] = np.nan
        kpi_table.at[i, "pedalMax"] = np.nan
        kpi_table.at[i, "pedalInc"] = np.nan
        kpi_table.at[i, "isPedalHigh"] = False
        kpi_table.at[i, "isPedalOnAtStrt"] = False
        return

    # Pedal start
    pedal_start = throttle[aeb_start_idx]
    kpi_table.at[i, "pedalStart"] = float(pedal_start)
    kpi_table.at[i, "isPedalOnAtStrt"] = pedal_start != 0

    # Max after AEB start
    throttle_range = throttle[aeb_start_idx:]
    pedal_max = float(np.max(throttle_range))
    kpi_table.at[i, "pedalMax"] = pedal_max

    # Increment and high flag
    pedal_inc = pedal_max - pedal_start
    kpi_table.at[i, "pedalInc"] = float(pedal_inc)
    kpi_table.at[i, "isPedalHigh"] = pedal_inc > pedal_pos_inc_th
