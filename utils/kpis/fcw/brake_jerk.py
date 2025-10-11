import numpy as np

def brake_jerk_duration(time, accel, fcw_request, window_s: float = 1.0,
                        jerk_thresh: float | None = None, mad_scale: float = 4.0,
                        return_all: bool = False):
    """
    Compute the duration of the brake jerk (bowl-shaped deceleration)
    after fcwRequest rises to 3, using jerk (d(accel)/dt).

    Duration = time between first negative jerk crossing (< -T)
               and first positive jerk crossing (> +T)
               within 1 s after FCW rises to 3.

    Parameters
    ----------
    time : array-like
        Time vector (s, sorted ascending).
    accel : array-like
        Filtered longitudinal acceleration signal.
    fcw_request : array-like
        FCW request signal (integer or float, typically 0–3).
    window_s : float
        Duration after FCW=3 rising edge to search (default 1 s).
    jerk_thresh : float or None
        Fixed jerk threshold (m/s³). If None, uses adaptive MAD-based threshold.
    mad_scale : float
        Scaling factor for adaptive threshold (default 4×MAD).
    return_all : bool
        Return list of all jerk events if multiple FCW=3 transitions exist.

    Returns
    -------
    (duration, t_start, t_end, threshold)
    """

    t = np.asarray(time, dtype=float)
    a = np.asarray(accel, dtype=float)
    r = np.asarray(fcw_request, dtype=float)

    if len(t) < 3 or np.any(np.diff(t) <= 0):
        raise ValueError("Time vector must be strictly increasing and long enough.")

    # --- compute jerk directly (no filtering) ---
    j = np.gradient(a, t)

    # --- detect FCW rising edges (→3) ---
    edges = np.where((r[:-1] < 3) & (r[1:] >= 3))[0]
    results = []

    for idx in edges:
        t0 = t[idx + 1]
        mask = (t >= t0) & (t <= t0 + window_s)
        if not np.any(mask):
            continue

        tw = t[mask]
        jw = j[mask]

        # --- adaptive threshold if not provided ---
        if jerk_thresh is None:
            med = np.median(jw)
            mad = np.median(np.abs(jw - med)) + 1e-12
            thr = max(0.5, mad_scale * 1.4826 * mad)
        else:
            thr = float(jerk_thresh)

        # find negative and positive jerk crossings
        neg_idx = np.where(jw < -thr)[0]
        if len(neg_idx) == 0:
            continue
        i0 = neg_idx[0]

        pos_idx = np.where(jw[i0 + 1:] > thr)[0]
        if len(pos_idx) == 0:
            continue
        i1 = i0 + 1 + pos_idx[0]

        duration = tw[i1] - tw[i0]
        results.append((duration, tw[i0], tw[i1], thr))

    if return_all:
        return results
    return results[0] if results else (None, None, None, None)
