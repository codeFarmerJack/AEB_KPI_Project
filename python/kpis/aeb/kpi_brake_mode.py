import numpy as np
import pandas as pd
import warnings

def kpi_brake_mode(obj, i, aeb_start_idx):
    """
    Determine if PB and FB are activated during AEB event.
    Updates obj.kpi_table in-place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict-like with arrays {time, aebTargetDecel}
        - PB_TGT_DECEL : float
        - FB_TGT_DECEL : float
        - TGT_TOL : float
    i : int
        Index of the file in kpi_table.
    aeb_start_idx : int
        Index of AEB request event.
    """
    kpi_table = obj.kpi_table
    signals = obj.signal_mat_chunk
    PB_TGT_DECEL = obj.PB_TGT_DECEL
    FB_TGT_DECEL = obj.FB_TGT_DECEL
    TGT_TOL = obj.TGT_TOL

    aeb_end_req = len(signals["time"]) - 1  # equivalent to MATLAB length()

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
    segment = signals["aebTargetDecel"][aeb_start_idx:aeb_end_req + 1]

    # Find PB / FB candidate indices
    pb_idx = np.where(np.abs(segment - PB_TGT_DECEL) <= TGT_TOL)[0]
    fb_idx = np.where(np.abs(segment - FB_TGT_DECEL) <= TGT_TOL)[0]

    is_pb_on = len(pb_idx) > 0
    is_fb_on = len(fb_idx) > 0

    # PB duration
    if is_pb_on:
        pb_start = aeb_start_idx + pb_idx[0]
        pb_end = aeb_start_idx + pb_idx[-1]
        pb_dur = signals["time"][pb_end] - signals["time"][pb_start]

        pb_dur_value = float(pb_dur)
        if np.isfinite(pb_dur_value):
            kpi_table.at[i, "pbDur"] = round(pb_dur_value, 2)
        else:
            warnings.warn(f"Invalid pbDur value for file index {i}: {pb_dur}. Setting pbDur to 0.")
            kpi_table.at[i, "pbDur"] = 0.0
    else:
        kpi_table.at[i, "pbDur"] = 0.0

    # FB duration
    if is_fb_on:
        fb_start = aeb_start_idx + fb_idx[0]
        fb_end = aeb_start_idx + fb_idx[-1]
        fb_dur = signals["time"][fb_end] - signals["time"][fb_start]

        fb_dur_value = float(fb_dur)
        if np.isfinite(fb_dur_value):
            kpi_table.at[i, "fbDur"] = round(fb_dur_value, 2)
        else:
            warnings.warn(f"Invalid fbDur value for file index {i}: {fb_dur}. Setting fbDur to 0.")
            kpi_table.at[i, "fbDur"] = 0.0
    else:
        kpi_table.at[i, "fbDur"] = 0.0

    # Flags
    kpi_table.at[i, "isPBOn"] = is_pb_on
    kpi_table.at[i, "isFBOn"] = is_fb_on
