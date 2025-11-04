import numpy as np

def detect_lsaeb_events(time, cpm_event_type, merge_window: float = 2.0):
    """
    Detect start and end times of LSAEB (Low-Speed AEB) events.

    Parameters
    ----------
    time : np.ndarray
        Time vector (seconds, increasing).
    cpm_event_type : np.ndarray
        CPM event type signal (0, 1, 2, ...).
    merge_window : float, optional
        If two LSAEB activations occur within this window (s), merge them.

    Returns
    -------
    start_times : np.ndarray
        Start times of merged LSAEB events.
    end_times : np.ndarray
        End times of merged LSAEB events.
    """

    time = np.asarray(time, dtype=float)
    cpm = np.asarray(cpm_event_type, dtype=float)

    if len(time) != len(cpm) or len(time) == 0:
        raise ValueError("Input arrays must be same length and non-empty.")

    # Compute previous-sample shift
    cpm_prev = np.roll(cpm, 1)
    cpm_prev[0] = cpm[0]

    # Rising edge: 0 → 1 or 2
    start_idx = np.where((cpm_prev == 0) & ((cpm == 1) | (cpm == 2)))[0]

    # Falling edge: 1/2 → 0
    end_idx = np.where(((cpm_prev == 1) | (cpm_prev == 2)) & (cpm == 0))[0]

    start_times = time[start_idx]
    end_times   = time[end_idx]

    # Handle unclosed last event (if LSAEB stays active till end)
    if len(start_times) > len(end_times):
        end_times = np.append(end_times, time[-1])

    if len(start_times) == 0:
        return np.array([]), np.array([])

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
