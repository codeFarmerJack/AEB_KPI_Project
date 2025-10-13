import numpy as np

def detect_aeb_events(time, aeb_target_decel, start_decel_delta=-30.0,
                      end_decel_delta=29.0, pb_tgt_decel=-6.0,
                      post_time=3.0):
    """
    Detect start and end times of AEB (Autonomous Emergency Braking) events.

    Parameters
    ----------
    time : np.ndarray
        Time vector (seconds, increasing).
    aeb_target_decel : np.ndarray
        AEB target deceleration signal.
    start_decel_delta : float, optional
        Threshold for strong negative decel delta (AEB start).
    end_decel_delta : float, optional
        Threshold for positive decel delta (AEB end).
    pb_tgt_decel : float, optional
        Deceleration threshold for PB activation (start mask).
    post_time : float, optional
        Fallback end time if end not found (seconds).

    Returns
    -------
    start_times : np.ndarray
        Detected AEB start times.
    end_times : np.ndarray
        Detected AEB end times.
    """

    time = np.asarray(time, dtype=float)
    decel = np.asarray(aeb_target_decel, dtype=float)

    if len(time) != len(decel) or len(time) == 0:
        raise ValueError("Input arrays must be the same length and non-empty.")

    # First derivative of deceleration
    delta = np.diff(decel)

    # --- Start detection ---
    locate_start = np.where(np.diff(delta < start_decel_delta))[0]
    start_mask = decel[locate_start + 1] <= pb_tgt_decel
    start_times = time[locate_start][start_mask]

    # --- End detection ---
    locate_end = np.where(delta > end_decel_delta)[0]
    end_times = time[locate_end]

    # --- Handle missing end events ---
    if len(end_times) == 0 and len(start_times) > 0:
        buffer_time = max(1.0, post_time + 4)
        end_times = start_times + buffer_time

    return np.array(start_times), np.array(end_times)
