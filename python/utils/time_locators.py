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


def detect_kneepoint(time, acc, direction="positive", cutoff_freq=5.0, method="curvature"):
    """
    Detect knee point in acceleration data (Python version of detectKneepoint_v4.m).

    Parameters
    ----------
    time : array-like
        Time vector (numeric seconds or datetime64).
    acc : array-like
        Acceleration values.
    direction : str, optional
        "positive" or "negative". Determines slope/curvature direction to consider.
    cutoff_freq : float, optional
        Cutoff frequency for low-pass Butterworth filter (Hz).
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
    time = np.asarray(time).ravel()
    acc = np.asarray(acc).ravel()

    # Convert datetime64 → seconds if needed
    if np.issubdtype(time.dtype, np.datetime64):
        time_sec = (time - time[0]) / np.timedelta64(1, "s")
    else:
        time_sec = time

    # Sampling frequency
    dt = np.mean(np.diff(time_sec))
    fs = 1.0 / dt

    # Design Butterworth low-pass filter
    b, a = butter(4, cutoff_freq / (fs / 2), btype="low")
    acc_filtered = filtfilt(b, a, acc)

    # First and second derivatives
    d_acc = np.gradient(acc_filtered, dt)
    dd_acc = np.gradient(d_acc, dt)

    # Detect turning points (local minima/maxima in first derivative)
    local_max_idx = argrelextrema(d_acc, np.greater)[0]
    local_min_idx = argrelextrema(d_acc, np.less)[0]
    turning_point_idx = np.unique(np.concatenate([local_max_idx, local_min_idx]))

    # Apply direction filter
    if direction.lower() == "positive":
        slope_mask = d_acc > 0
        curvature_mask = dd_acc > 0
    elif direction.lower() == "negative":
        slope_mask = d_acc < 0
        curvature_mask = dd_acc < 0
    else:
        raise ValueError('direction must be either "positive" or "negative".')

    # Select detection method
    if method.lower() == "curvature":
        dd_acc_filtered = np.abs(dd_acc).copy()
        dd_acc_filtered[~curvature_mask] = -np.inf
        knee_idx = int(np.argmax(dd_acc_filtered))
    elif method.lower() == "slope":
        d_acc_filtered = np.abs(d_acc).copy()
        d_acc_filtered[~slope_mask] = -np.inf
        knee_idx = int(np.argmax(d_acc_filtered))
    else:
        raise ValueError('method must be either "curvature" or "slope".')

    # Extract knee time and value
    knee_time = time[knee_idx]
    knee_value = acc[knee_idx]

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
    m0 : scalar or None
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
        m0 = signal_chunk["time"][first_idx]
        return first_idx, m0
    else:
        return None, None


def find_aeb_intv_end(signal_chunk, aeb_start_idx, aeb_end_thd):
    """
    Detect the end of an AEB intervention.

    Parameters
    ----------
    signal_chunk : dict-like or object with attributes
        Must contain:
          - time (array-like)
          - egoSpeed (array-like)
          - aebTargetDecel (array-like)
    aeb_start_idx : int
        Index of AEB request event.
    aeb_end_thd : float
        Threshold for AEB intervention end.

    Returns
    -------
    is_veh_stopped : bool
        True if vehicle stopped during intervention.
    aeb_end_idx : int
        Index of AEB intervention end.
    m2 : scalar
        Timestamp of AEB intervention end.
    """
    time = np.asarray(signal_chunk["time"])
    ego_speed = np.asarray(signal_chunk["egoSpeed"])
    aeb_target_decel = np.asarray(signal_chunk["aebTargetDecel"])

    # slice from intervention start
    decel_slice = aeb_target_decel[aeb_start_idx:]
    speed_slice = ego_speed[aeb_start_idx:]

    # 1. Check if intervention end condition (decel threshold crossed) occurs
    intv_end_rel_idx = np.argmax(decel_slice > aeb_end_thd) if np.any(decel_slice > aeb_end_thd) else None
    is_intv_end = intv_end_rel_idx is not None

    # 2. Check if vehicle stops in the window
    veh_stop_rel_idx = np.argmax(speed_slice == 0) if np.any(speed_slice == 0) else None
    is_veh_stopped = veh_stop_rel_idx is not None

    # 3. Determine final end index
    if is_intv_end and is_veh_stopped:
        aeb_end_idx = min(
            aeb_start_idx + intv_end_rel_idx,
            aeb_start_idx + veh_stop_rel_idx,
        )
    elif not is_intv_end and is_veh_stopped:
        aeb_end_idx = aeb_start_idx + veh_stop_rel_idx
    elif is_intv_end and not is_veh_stopped:
        aeb_end_idx = aeb_start_idx + intv_end_rel_idx
    else:
        aeb_end_idx = len(time) - 1  # default: last timestamp

    m2 = time[aeb_end_idx]

    return is_veh_stopped, aeb_end_idx, m2
