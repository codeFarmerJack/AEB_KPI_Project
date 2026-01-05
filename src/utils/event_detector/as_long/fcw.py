import numpy as np

def detect_fcw_events(time, fcw_request, merge_window: float = 2.0):
    """
    Detect start and end times of FCW (Forward Collision Warning) events.

    Parameters
    ----------
    time : np.ndarray
        Time vector (seconds, increasing).
    fcw_request : np.ndarray
        FCW request signal (0, 1, 2, or 3).
    merge_window : float, optional
        If two FCW activations occur within this window (s), merge them.

    Returns
    -------
    start_times : np.ndarray
        Start times of merged FCW events.
    end_times : np.ndarray
        End times of merged FCW events.
    """

    time = np.asarray(time, dtype=float)
    fcw = np.asarray(fcw_request, dtype=float)

    if len(time) != len(fcw) or len(time) == 0:
        raise ValueError("Input arrays must be same length and non-empty.")

    # Compute previous-sample shift
    fcw_prev = np.roll(fcw, 1)
    fcw_prev[0] = fcw[0]

    # Rising edge: 0 → 2 or 3
    start_idx = np.where((fcw_prev == 0) & ((fcw == 2) | (fcw == 3)))[0]

    # Falling edge: 2/3 → 0
    end_idx = np.where(((fcw_prev == 2) | (fcw_prev == 3)) & (fcw == 0))[0]

    if start_idx.size == 0:
        return np.array([]), np.array([])

    # Pair each start with the next end after it
    pos = np.searchsorted(end_idx, start_idx, side="right")
    has_end = pos < end_idx.size

    start_times = time[start_idx]
    end_times = np.empty_like(start_times)
    if has_end.any():
        end_times[has_end] = time[end_idx[pos[has_end]]]
    if (~has_end).any():
        end_times[~has_end] = time[-1]
        for t in start_times[~has_end]:
            print(f"⚠️ No FCW end found after {t:.3f}s — using end of log.")

    # Merge events that occur close together
    merged_starts, merged_ends = [], []
    cur_s, cur_e = start_times[0], end_times[0]

    for i in range(1, len(start_times)):
        ns, ne = start_times[i], end_times[i]
        if ns - cur_e <= merge_window:
            cur_e = ne
        else:
            merged_starts.append(cur_s)
            merged_ends.append(cur_e)
            cur_s, cur_e = ns, ne

    merged_starts.append(cur_s)
    merged_ends.append(cur_e)

    return np.array(merged_starts), np.array(merged_ends)
