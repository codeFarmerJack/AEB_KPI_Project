import numpy as np
import pandas as pd

def throttle(mdf, kpi_table, row_idx, aeb_start_idx, pedal_pos_inc_th):
    """
    Throttle pedal KPIs during an AEB event.
    Updates kpi_table in place.

    KPIs extracted:
    - pedalPosAtStart : Pedal position at start of AEB intervention
    - pedalPosMax     : Maximum pedal position during AEB intervention
    - pedalPosInc     : Increment (Max - Start)
    - isPedalPosIncHigh : True if pedalPosInc exceeds threshold
    - isPedalOnAtStrt : True if pedal was pressed at AEB start
    """
    # Ensure required columns exist with correct dtype
    for col, default, dtype in [
        ("pedalPosAtStart", np.nan, "float"),
        ("pedalPosMax", np.nan, "float"),
        ("pedalPosInc", np.nan, "float"),
        ("isPedalPosIncHigh", False, "boolean"),
        ("isPedalOnAtStrt", False, "boolean"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    try:
        throttle = np.asarray(mdf.throttleValue)
    except AttributeError:
        # Missing signal → set defaults
        kpi_table.at[row_idx, "pedalPosAtStart"]    = np.nan
        kpi_table.at[row_idx, "pedalPosMax"]        = np.nan
        kpi_table.at[row_idx, "pedalPosInc"]        = np.nan
        kpi_table.at[row_idx, "isPedalPosIncHigh"]  = False
        kpi_table.at[row_idx, "isPedalOnAtStrt"]    = False
        return

    # Validate aeb_start_idx
    if (
        aeb_start_idx is None
        or aeb_start_idx < 0
        or aeb_start_idx >= len(throttle)
    ):
        kpi_table.at[row_idx, "pedalPosAtStart"]    = np.nan
        kpi_table.at[row_idx, "pedalPosMax"]        = np.nan
        kpi_table.at[row_idx, "pedalPosInc"]        = np.nan
        kpi_table.at[row_idx, "isPedalPosIncHigh"]  = False
        kpi_table.at[row_idx, "isPedalOnAtStrt"]    = False
        return

    # Pedal at start
    pedal_start = float(throttle[aeb_start_idx])
    kpi_table.at[row_idx, "pedalPosAtStart"] = pedal_start
    kpi_table.at[row_idx, "isPedalOnAtStrt"] = (pedal_start != 0)

    # Max pedal after AEB start
    throttle_range = throttle[aeb_start_idx:]
    pedal_max = float(np.max(throttle_range)) if len(throttle_range) else np.nan
    kpi_table.at[row_idx, "pedalPosMax"] = pedal_max

    # Increment
    if np.isfinite(pedal_max) and np.isfinite(pedal_start):
        pedal_inc = pedal_max - pedal_start
    else:
        pedal_inc = np.nan

    kpi_table.at[row_idx, "pedalPosInc"] = pedal_inc if np.isfinite(pedal_inc) else np.nan

    # Threshold flag
    kpi_table.at[row_idx, "isPedalPosIncHigh"] = (
        pedal_inc > pedal_pos_inc_th if np.isfinite(pedal_inc) else False
    )
