import numpy as np
from scipy.signal import butter, filtfilt

def accel_filter(time, acc, cutoff_freq):
    time = np.asarray(time).ravel()
    acc = np.asarray(acc).ravel()

    if np.issubdtype(time.dtype, np.datetime64):
        time = (time - time[0]) / np.timedelta64(1, "s")

    dt = np.mean(np.diff(time))
    fs = 1.0 / dt

    b, a = butter(4, cutoff_freq / (fs / 2), btype="low")
    return filtfilt(b, a, acc)
