import numpy as np

def detect_lka_events(time, lka_intervention_status, output: str = "indices"):
    """
    Detect LKA (Lane Keeping Assist) intervention events.
    Start: rising edge (0 -> 1)
    End:   falling edge (1 -> 0)

    Parameters
    ----------
    time : np.ndarray
        Time vector (seconds, increasing).
    lka_intervention_status : np.ndarray
        LKA status signal (0 = inactive, 1 = active).
    output : {"indices", "times"}, optional
        Return event indices or times. Default is "indices".

    Returns
    -------
    starts, ends : np.ndarray, np.ndarray
        Start and end arrays in the requested format.
    """
    time = np.asarray(time, dtype=float)
    sig  = np.asarray(lka_intervention_status, dtype=float)

    if len(time) != len(sig) or len(time) == 0:
        raise ValueError("Input arrays must be same length and non-empty.")

    n = len(time)

    # previous-sample shift
    sig_prev = np.roll(sig, 1)
    sig_prev[0] = sig[0]

    # Detect rising (0->1) and falling (1->0) edges
    start_idx = np.where((sig_prev == 0) & (sig == 1))[0]
    end_idx   = np.where((sig_prev == 1) & (sig == 0))[0]

    # Handle open-ended events (active at end of log)
    if len(start_idx) > len(end_idx):
        end_idx = np.append(end_idx, n - 1)

    start_idx = np.clip(start_idx, 0, n - 1)
    end_idx   = np.clip(end_idx,   0, n - 1)

    if len(start_idx) == 0:
        print("⚠️ No LKA events detected.")
        return (np.array([], dtype=int) if output == "indices" else np.array([]),
                np.array([], dtype=int) if output == "indices" else np.array([]))

    # --- Friendly debug print ---
    print("\n🧩 Detected LKA events:")
    for si, ei in zip(start_idx, end_idx):
        print(f"   ➝ Start idx={si:6d} (t={time[si]:.3f}s), End idx={ei:6d} (t={time[ei]:.3f}s)")
    print(f"   Total events detected: {len(start_idx)}\n")

    # --- Return format ---
    if output == "indices":
        return start_idx, end_idx
    elif output == "times":
        return time[start_idx], time[end_idx]
    else:
        raise ValueError("output must be 'indices' or 'times'")
