import numpy as np
import pandas as pd

def kpi_steering_wheel(obj, i, aeb_start_idx, steer_ang_th, steer_ang_rate_th):
    """
    Steering wheel analysis during an AEB event.
    Updates obj.kpi_table in place.

    Parameters
    ----------
    obj : object with attributes
        - kpi_table : pandas.DataFrame
        - signal_mat_chunk : dict with arrays {steerWheelAngle, steerWheelAngleSpeed}
        - TIME_IDX_OFFSET : int
    i : int
        Row index in kpi_table to update.
    aeb_start_idx : int
        Index of AEB request event.
    steer_ang_th : float
        Threshold for steering angle in degrees.
    steer_ang_rate_th : float
        Threshold for steering angle rate in degrees/sec.
    """
    kpi_table = obj.kpi_table
    signals = obj.signal_mat_chunk
    offset = obj.TIME_IDX_OFFSET

    # Ensure required columns exist
    for col, default, dtype in [
        ("steerMax", np.nan, "float"),
        ("absSteerMaxDeg", np.nan, "float"),
        ("isSteerHigh", False, "bool"),
        ("steerRateMax", np.nan, "float"),
        ("absSteerRateMaxDeg", np.nan, "float"),
        ("isSteerAngRateHigh", False, "bool"),
    ]:
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

    # Steering angle
    segment_angle = signals["steerWheelAngle"][aeb_start_idx - offset :]
    idx_rel = int(np.argmax(np.abs(segment_angle)))
    steer_max = segment_angle[idx_rel]
    abs_steer_max_deg = round(abs(steer_max * 180 / np.pi), 2)

    kpi_table.at[i, "steerMax"] = float(steer_max)
    kpi_table.at[i, "absSteerMaxDeg"] = abs_steer_max_deg
    kpi_table.at[i, "isSteerHigh"] = abs_steer_max_deg > steer_ang_th

    # Steering angle rate
    segment_rate = signals["steerWheelAngleSpeed"][aeb_start_idx - offset :]
    idx_rel_rate = int(np.argmax(np.abs(segment_rate)))
    steer_rate_max = segment_rate[idx_rel_rate]
    abs_steer_rate_max_deg = round(abs(steer_rate_max * 180 / np.pi), 2)

    kpi_table.at[i, "steerRateMax"] = float(steer_rate_max)
    kpi_table.at[i, "absSteerRateMaxDeg"] = abs_steer_rate_max_deg
    kpi_table.at[i, "isSteerAngRateHigh"] = abs_steer_rate_max_deg > steer_ang_rate_th
