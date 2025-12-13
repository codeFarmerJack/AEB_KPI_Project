import numpy as np
from scipy.signal import butter, filtfilt

def accel_filter(time, acc, cutoff_freq, order=4):
    """
    Apply a low-pass Butterworth filter to acceleration signal.

    Parameters
    ----------
    time : array-like
        Time vector (float or datetime64).
    acc : array-like
        Acceleration signal.
    cutoff_freq : float
        Cutoff frequency in Hz.
    order : int
        Filter order (default = 4).

    Returns
    -------
    filtered : np.ndarray
        Filtered acceleration signal (same shape as input).
    """
    time = np.asarray(time).ravel()
    acc = np.asarray(acc).ravel()

    if len(time) < order * 3:  # padlen rule of thumb
        # Not enough points → just return original
        return acc

    # Handle datetime64
    if np.issubdtype(time.dtype, np.datetime64):
        time = (time - time[0]) / np.timedelta64(1, "s")

    # Sampling interval
    dt = np.mean(np.diff(time))
    if not np.isfinite(dt) or dt <= 0:
        dt = 1.0
    fs = 1.0 / dt

    # Prevent invalid cutoff (Nyquist guard)
    nyq = fs / 2.0
    if cutoff_freq >= nyq:
        cutoff_freq = 0.99 * nyq  # clamp to Nyquist

    # Replace NaNs/Infs with 0
    acc = np.nan_to_num(acc, nan=0.0, posinf=0.0, neginf=0.0)

    b, a = butter(order, cutoff_freq / nyq, btype="low")
    try:
        return filtfilt(b, a, acc)
    except ValueError:
        # fallback if filtfilt still fails (short signal or unstable)
        return acc
