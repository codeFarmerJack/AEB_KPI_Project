import numpy as np
from scipy.signal import argrelextrema

import numpy as np
import warnings

def detect_aeb_events(time, aeb_request, post_time=3.0):
    """
    Detect AEB (Autonomous Emergency Braking) events based on aebRequest signal transitions.

    Logic
    -----
    • Start → when aebRequest changes *to* 1 or 2.
    • End   → when aebRequest changes *from* 1, 2, or 3 *to* 0.

    Parameters
    ----------
    time : np.ndarray
        Time vector (seconds, monotonically increasing).
    aeb_request : np.ndarray
        Integer or float signal representing AEB request state (e.g., 0, 1, 2, 3).
    post_time : float, optional
        Safety buffer if an end is not detected before the signal ends.

    Returns
    -------
    start_times : np.ndarray
        Detected AEB start times.
    end_times : np.ndarray
        Detected AEB end times.
    """

    time = np.asarray(time, dtype=float)
    req = np.asarray(aeb_request, dtype=float)

    if len(time) != len(req) or len(time) == 0:
        raise ValueError("Input arrays must be the same length and non-empty.")

    # --- Identify transitions ---
    start_indices = []
    end_indices = []

    for i in range(1, len(req)):
        prev, curr = req[i - 1], req[i]

        # Detect rising transition → AEB start
        if curr in (1, 2) and prev not in (1, 2):
            start_indices.append(i)

        # Detect falling transition → AEB end
        if prev in (1, 2, 3) and curr == 0:
            end_indices.append(i)

    # --- Pair start and end events ---
    start_times = []
    end_times = []

    for s in start_indices:
        # Find first end index after this start
        e_candidates = [e for e in end_indices if e > s]
        if e_candidates:
            e = e_candidates[0]
            start_times.append(time[s])
            end_times.append(time[e])
        else:
            # No matching end found → fallback to +post_time
            start_times.append(time[s])
            end_times.append(min(time[-1], time[s] + post_time))
            warnings.warn(f"⚠️ No AEB end found after {time[s]:.3f}s — used +{post_time:.1f}s buffer.")

    return np.array(start_times), np.array(end_times)


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

