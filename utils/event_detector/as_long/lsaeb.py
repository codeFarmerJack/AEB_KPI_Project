import numpy as np

def detect_lsaeb_events(time, cpm_event_type, merge_window: float = 2.0):
    """
    Detect start and end indices of LSAEB (Low-Speed AEB) events.
    Works safely for both full-length and segmented recordings.
    """

    time = np.asarray(time, dtype=float)
    cpm = np.asarray(cpm_event_type, dtype=float)

    if len(time) != len(cpm) or len(time) == 0:
        raise ValueError("Input arrays must be same length and non-empty.")

    n = len(time)

    # Compute previous-sample shift
    cpm_prev = np.roll(cpm, 1)
    cpm_prev[0] = cpm[0]

    # Rising edge: 0 → 1 or 2
    start_idx = np.where((cpm_prev == 0) & ((cpm == 1) | (cpm == 2)))[0]

    # Falling edge: 1/2 → 0
    end_idx = np.where(((cpm_prev == 1) | (cpm_prev == 2)) & (cpm == 0))[0]

    # Handle open-ended events (still active at end)
    if len(start_idx) > len(end_idx):
        end_idx = np.append(end_idx, n - 1)

    # Clip out-of-range indices (important for segmented data)
    start_idx = np.clip(start_idx, 0, n - 1)
    end_idx = np.clip(end_idx, 0, n - 1)

    if len(start_idx) == 0:
        print("⚠️ No LSAEB events detected.")
        return np.array([]), np.array([])

    # --- Merge close events ---
    merged_starts, merged_ends = [], []
    cur_s, cur_e = start_idx[0], end_idx[0]

    for i in range(1, len(start_idx)):
        ns, ne = start_idx[i], end_idx[i]
        if time[ns] - time[cur_e] <= merge_window:
            cur_e = ne
        else:
            merged_starts.append(cur_s)
            merged_ends.append(cur_e)
            cur_s, cur_e = ns, ne

    merged_starts.append(cur_s)
    merged_ends.append(cur_e)

    # Final clipping again just in case
    merged_starts = np.clip(np.array(merged_starts, dtype=int), 0, n - 1)
    merged_ends   = np.clip(np.array(merged_ends, dtype=int), 0, n - 1)

    # --- Debug print ---
    print("\n🧩 Detected LSAEB events:")
    for si, ei in zip(merged_starts, merged_ends):
        print(f"   ➝ Start idx={si:6d} (t={time[si]:.3f}s), End idx={ei:6d} (t={time[ei]:.3f}s)")
    print(f"   Total events detected: {len(merged_starts)}\n")

    return time[merged_starts], time[merged_ends]
