import numpy as np

def detect_decel_onset(jerk: np.ndarray, neg_thd: float):
    """
    Detect the start index of a deceleration event.

    Parameters
    ----------
    jerk : np.ndarray
        Jerk signal (derivative of acceleration).
    neg_thd : float
        Negative jerk threshold (m/s³).

    Returns
    -------
    start_idx : int or None
        Index of the first sample where deceleration onset occurs.
    """
    neg_idx = np.where(jerk < neg_thd)[0]
    return int(neg_idx[0]) if len(neg_idx) > 0 else None


def detect_brake_jerk_end(jerk: np.ndarray, pos_thd: float, start_idx: int):
    """
    Detect the end index of a braking jerk event (positive recovery after braking).

    Parameters
    ----------
    jerk : np.ndarray
        Jerk signal (derivative of acceleration).
    pos_thd : float
        Positive jerk threshold (m/s³).
    start_idx : int
        Start index returned by detect_decel_onset().

    Returns
    -------
    end_idx : int or None
        Index of the last positive jerk exceeding pos_thd after start_idx, or None if not found.
    """
    if start_idx is None:
        return None
    pos_idx = np.where(jerk > pos_thd)[0]
    if len(pos_idx) == 0:
        return None
    pos_after_start = pos_idx[pos_idx > start_idx]
    return int(pos_after_start[-1]) if len(pos_after_start) > 0 else None
