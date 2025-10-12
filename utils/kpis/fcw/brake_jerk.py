import numpy as np

def brake_jerk(time, accel, fcw_request, window_s: float = 1.0,
               jerk_thresh: float | None = None, mad_scale: float = 4.0,
               return_all: bool = False):
    """
    Compute key brake jerk KPIs (duration, max jerk, max acceleration)
    after FCW request rises to 3.

    This function internally calls three sub-functions:
      - _duration(): computes jerk duration (bowl-shaped region)
      - _max_jerk(): computes maximum jerk magnitude (placeholder)
      - _max_accel(): computes maximum acceleration (placeholder)

    Parameters
    ----------
    time : array-like
        Time vector (s, sorted ascending).
    accel : array-like
        Filtered longitudinal acceleration signal.
    fcw_request : array-like
        FCW request signal (integer or float, typically 0–3).
    window_s : float, optional
        Duration after FCW=3 rising edge to search (default 1 s).
    jerk_thresh : float or None, optional
        Fixed jerk threshold (m/s³). If None, uses adaptive MAD-based threshold.
    mad_scale : float, optional
        Scaling factor for adaptive threshold (default 4×MAD).
    return_all : bool, optional
        If True, returns all detected events. Default False (first event only).

    Returns
    -------
    dict
        {
            "duration": float or None,
            "t_start": float or None,
            "t_end": float or None,
            "threshold": float or None,
            "max_jerk": float or None,
            "max_accel": float or None
        }
    """

    # --- 1️⃣ Compute brake jerk duration ---
    duration, t_start, t_end, threshold = _duration(
        time, accel, fcw_request,
        window_s=window_s,
        jerk_thresh=jerk_thresh,
        mad_scale=mad_scale,
        return_all=return_all
    )

    # --- 2️⃣ Compute max jerk (placeholder) ---
    max_jerk = _max_jerk(time, accel, fcw_request)

    # --- 3️⃣ Compute max acceleration (placeholder) ---
    max_accel = _max_accel(time, accel, fcw_request)

    return {
        "duration": duration,
        "t_start": t_start,
        "t_end": t_end,
        "threshold": threshold,
        "max_jerk": max_jerk,
        "max_accel": max_accel
    }


# ------------------------------------------------------------------ #
# 🔹 Sub-function 1: Compute jerk duration (fully implemented)
# ------------------------------------------------------------------ #
def _duration(time, accel, fcw_request, window_s=1.0,
              jerk_thresh=None, mad_scale=4.0, return_all=False):
    """Duration of bowl-shaped jerk region after FCW=3 rise."""
    t = np.asarray(time, dtype=float)
    a = np.asarray(accel, dtype=float)
    r = np.asarray(fcw_request, dtype=float)

    if len(t) < 3 or np.any(np.diff(t) <= 0):
        raise ValueError("Time vector must be strictly increasing and long enough.")

    # Compute jerk directly (no extra filtering)
    j = np.gradient(a, t)

    # Detect FCW rising edges (→3)
    edges = np.where((r[:-1] < 3) & (r[1:] >= 3))[0]
    results = []

    for idx in edges:
        t0 = t[idx + 1]
        mask = (t >= t0) & (t <= t0 + window_s)
        if not np.any(mask):
            continue

        tw = t[mask]
        jw = j[mask]

        # Adaptive threshold
        if jerk_thresh is None:
            med = np.median(jw)
            mad = np.median(np.abs(jw - med)) + 1e-12
            thr = max(0.5, mad_scale * 1.4826 * mad)
        else:
            thr = float(jerk_thresh)

        # Negative and positive jerk crossings
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


# ------------------------------------------------------------------ #
# 🔹 Sub-function 2: Compute max jerk (placeholder)
# ------------------------------------------------------------------ #
def _max_jerk(time, accel, fcw_request):
    """
    Placeholder for maximum jerk magnitude computation.
    To be implemented later.
    """
    # TODO: Implement jerk magnitude analysis within FCW window
    return None


# ------------------------------------------------------------------ #
# 🔹 Sub-function 3: Compute max acceleration (placeholder)
# ------------------------------------------------------------------ #
def _max_accel(time, accel, fcw_request):
    """
    Placeholder for maximum acceleration computation.
    To be implemented later.
    """
    # TODO: Implement acceleration peak search within FCW window
    return None
