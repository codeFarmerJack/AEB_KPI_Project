import numpy as np
from scipy.signal import butter, filtfilt, argrelextrema

def find_closest_time(time_vector, target_time):
    """
    Find the value in time_vector closest to target_time.

    Parameters
    ----------
    time_vector : array-like
        Sequence of time values (numeric seconds or datetime64).
    target_time : float, int, or datetime64
        Target time to search for.

    Returns
    -------
    val : scalar
        The closest time value from time_vector.
    idx : int
        The index of val in time_vector.
    """
    time_vector = np.asarray(time_vector)

    # Handle datetime64 by converting target_time accordingly
    if np.issubdtype(time_vector.dtype, np.datetime64):
        if not np.issubdtype(np.asarray(target_time).dtype, np.datetime64):
            raise TypeError("target_time must be datetime64 if time_vector is datetime64")

    differences = np.abs(time_vector - target_time)
    idx = int(np.argmin(differences))
    val = time_vector[idx]

    return val, idx


def detect_kneepoint(time, accel, direction="positive", method="curvature"):
    """
    Detect knee point in acceleration data (Python version of detectKneepoint_v4.m).

    Parameters
    ----------
    time : array-like
        Time vector (numeric seconds or datetime64).
    accel : array-like
        Acceleration values (already filtered).
    direction : str, optional
        "positive" or "negative". Determines slope/curvature direction to consider.
    method : str, optional
        "curvature" or "slope". Detection method.

    Returns
    -------
    knee_idx : int
        Index of detected knee point.
    knee_time : float or datetime64
        Time at knee point.
    knee_value : float
        Acceleration at knee point.
    """
    # Convert inputs to numpy arrays
    time = np.asarray(time).ravel()
    accel = np.asarray(accel).ravel()

    # Convert datetime64 → seconds if needed
    if np.issubdtype(time.dtype, np.datetime64):
        time_sec = (time - time[0]) / np.timedelta64(1, "s")
    else:
        time_sec = time

    # Compute time step and first/second derivatives
    dt = np.mean(np.diff(time_sec))
    d_accel = np.gradient(accel, dt)
    dd_accel = np.gradient(d_accel, dt)

    # Find local extrema (turning points in first derivative)
    local_max_idx = argrelextrema(d_accel, np.greater)[0]
    local_min_idx = argrelextrema(d_accel, np.less)[0]
    turning_point_idx = np.unique(np.concatenate([local_max_idx, local_min_idx]))

    # Apply direction filters
    if direction.lower() == "positive":
        slope_mask = d_accel > 0
        curvature_mask = dd_accel > 0
    elif direction.lower() == "negative":
        slope_mask = d_accel < 0
        curvature_mask = dd_accel < 0
    else:
        raise ValueError('direction must be either "positive" or "negative".')

    # Select detection method
    if method.lower() == "curvature":
        dd_accel_filtered = np.abs(dd_accel).copy()
        dd_accel_filtered[~curvature_mask] = -np.inf
        knee_idx = int(np.argmax(dd_accel_filtered))
    elif method.lower() == "slope":
        d_accel_filtered = np.abs(d_accel).copy()
        d_accel_filtered[~slope_mask] = -np.inf
        knee_idx = int(np.argmax(d_accel_filtered))
    else:
        raise ValueError('method must be either "curvature" or "slope".')

    # Extract knee point info
    knee_time = time[knee_idx]
    knee_value = accel[knee_idx]

    return knee_idx, knee_time, knee_value


def find_first_last_indices(vector, target_value, comparison_mode="equal", tolerance=0.0):
    """
    Finds first and last indices of values matching a condition with optional tolerance.

    Parameters
    ----------
    vector : array-like
        Numeric vector to search.
    target_value : float
        Value to compare against.
    comparison_mode : str
        'equal', 'less', or 'greater'.
    tolerance : float, optional
        Allowed tolerance (default = 0.0).

    Returns
    -------
    first_idx : int or None
        Index of first match, or None if no matches.
    last_idx : int or None
        Index of last match, or None if no matches.
    all_idx : list[int]
        List of all matching indices.
    """
    vector = np.asarray(vector)

    if comparison_mode.lower() == "equal":
        condition = np.abs(vector - target_value) <= tolerance
    elif comparison_mode.lower() == "less":
        condition = vector < (target_value + tolerance)
    elif comparison_mode.lower() == "greater":
        condition = vector > (target_value - tolerance)
    else:
        raise ValueError("Invalid comparison_mode. Use 'equal', 'less', or 'greater'.")

    all_idx = np.where(condition)[0]

    if len(all_idx) == 0:
        return None, None, []
    else:
        first_idx = int(all_idx[0])
        last_idx = int(all_idx[-1])
        return first_idx, last_idx, all_idx.tolist()


def find_aeb_intv_start(signal_chunk, pb_tgt_decel):
    """
    Locate AEB intervention start.

    Parameters
    ----------
    signal_chunk : dict-like
        Must contain:
          - 'aebTargetDecel' : array-like
          - 'time' : array-like
    pb_tgt_decel : float
        Target deceleration threshold.

    Returns
    -------
    aeb_start_idx : int or None
        Index of AEB request event, or None if not found.
    aeb_start_time : scalar or None
        Timestamp of AEB intervention start.
    """
    if "aebTargetDecel" not in signal_chunk:
        return None, None

    # Use helper function to find indices
    first_idx, _, all_idx = find_first_last_indices(
        signal_chunk["aebTargetDecel"], 
        pb_tgt_decel, 
        comparison_mode="less", 
        tolerance=0.1
    )

    if first_idx is not None:
        aeb_start_time = signal_chunk["time"][first_idx]
        return first_idx, aeb_start_time
    else:
        return None, None


def find_aeb_intv_end(signal_chunk, aeb_start_idx, aeb_end_thd):
    """
    Detect the end of an AEB intervention.
    """
    time = np.asarray(signal_chunk.get("time", []))
    ego_speed = np.asarray(signal_chunk.get("egoSpeed", []))
    aeb_target_decel = np.asarray(signal_chunk.get("aebTargetDecel", []))

    # --- Defensive guards ---
    if len(time) == 0 or aeb_start_idx is None or aeb_start_idx < 0 or aeb_start_idx >= len(time):
        return False, None, np.nan

    # Slice from intervention start
    decel_slice = aeb_target_decel[aeb_start_idx:]
    speed_slice = ego_speed[aeb_start_idx:]

    # 1. Intervention end condition
    intv_end_rel_idx = np.argmax(decel_slice > aeb_end_thd) if np.any(decel_slice > aeb_end_thd) else None

    # 2. Vehicle stop condition
    veh_stop_rel_idx = np.argmax(speed_slice == 0) if np.any(speed_slice == 0) else None
    is_veh_stopped = veh_stop_rel_idx is not None

    # 3. Determine final end index
    if intv_end_rel_idx is not None and is_veh_stopped:
        aeb_end_idx = min(aeb_start_idx + intv_end_rel_idx,
                          aeb_start_idx + veh_stop_rel_idx)
    elif intv_end_rel_idx is None and is_veh_stopped:
        aeb_end_idx = aeb_start_idx + veh_stop_rel_idx
    elif intv_end_rel_idx is not None and not is_veh_stopped:
        aeb_end_idx = aeb_start_idx + intv_end_rel_idx
    else:
        # fallback: last sample only if time is not empty
        aeb_end_idx = len(time) - 1 if len(time) > 0 else None

    # 4. Resolve end time
    if aeb_end_idx is None or aeb_end_idx < 0 or aeb_end_idx >= len(time):
        return is_veh_stopped, None, np.nan

    aeb_end_time = float(time[aeb_end_idx])
    return is_veh_stopped, aeb_end_idx, aeb_end_time


