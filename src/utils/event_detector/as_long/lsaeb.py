import numpy as np

def detect_lsaeb_events(time, cpm_event_type, merge_window: float = 2.0, output: str = "indices"):
    """
    Detect LSAEB (Low-Speed AEB) events and return start/end as indices (default) or times.

    Parameters
    ----------
    time : np.ndarray
        Time vector (seconds, increasing).
    cpm_event_type : np.ndarray
        CPM event type signal (0, 1, 2, ...).
    merge_window : float, optional
        If two activations occur within this window (s), merge them. Default 2.0s.
    output : {"indices", "times"}, optional
        Format of returned arrays. Default "indices" for backward compatibility.

    Returns
    -------
    starts, ends : np.ndarray, np.ndarray
        Start and end arrays in the requested format.
    """
    time = np.asarray(time, dtype=float)
    cpm  = np.asarray(cpm_event_type, dtype=float)

    if len(time) != len(cpm) or len(time) == 0:
        raise ValueError("Input arrays must be same length and non-empty.")

    n = len(time)

    # previous-sample shift
    cpm_prev = np.roll(cpm, 1)
    cpm_prev[0] = cpm[0]

    # edges: 0 -> {1,2} ; {1,2} -> 0
    start_idx = np.where((cpm_prev == 0) & ((cpm == 1) | (cpm == 2)))[0]
    end_idx   = np.where(((cpm_prev == 1) | (cpm_prev == 2)) & (cpm == 0))[0]

    # handle open-ended events
    if len(start_idx) > len(end_idx):
        end_idx = np.append(end_idx, n - 1)

    # basic guards for segmented data
    start_idx = np.clip(start_idx, 0, n - 1)
    end_idx   = np.clip(end_idx,   0, n - 1)

    if len(start_idx) == 0:
        # keep prints for visibility; return empty arrays in requested format
        print("⚠️ No LSAEB events detected.")
        return (np.array([], dtype=int) if output == "indices" else np.array([]),
                np.array([], dtype=int) if output == "indices" else np.array([]))

    # merge close events in time
    merged_starts, merged_ends = [], []
    cur_s, cur_e = int(start_idx[0]), int(end_idx[0])

    for i in range(1, len(start_idx)):
        ns, ne = int(start_idx[i]), int(end_idx[i])
        if time[ns] - time[cur_e] <= merge_window:
            cur_e = ne
        else:
            merged_starts.append(cur_s)
            merged_ends.append(cur_e)
            cur_s, cur_e = ns, ne

    merged_starts.append(cur_s)
    merged_ends.append(cur_e)

    starts_idx = np.array(merged_starts, dtype=int)
    ends_idx   = np.array(merged_ends,   dtype=int)

    # friendly debug print
    print("\n🧩 Detected LSAEB events:")
    for si, ei in zip(starts_idx, ends_idx):
        print(f"   ➝ Start idx={si:6d} (t={time[si]:.3f}s), End idx={ei:6d} (t={time[ei]:.3f}s)")
    print(f"   Total events detected: {len(starts_idx)}\n")

    if output == "indices":
        return starts_idx, ends_idx
    elif output == "times":
        return time[starts_idx], time[ends_idx]
    else:
        raise ValueError("output must be 'indices' or 'times'")
