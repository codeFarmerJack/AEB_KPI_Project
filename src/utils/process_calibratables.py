import numpy as np

def extract_calibratables(cal_struct):
    calibratables = {}
    for category, category_struct in cal_struct.items():
        for signal_name, signal_struct in category_struct.items():
            if isinstance(signal_struct, dict):
                # if it has x/y, keep dict
                if "x" in signal_struct and "y" in signal_struct:
                    calibratables[signal_name] = {
                        "x": signal_struct["x"],
                        "y": signal_struct["y"]
                    }
                elif "Data" in signal_struct:  # fallback
                    calibratables[signal_name] = signal_struct["Data"]
                else:
                    print(f'⚠️ Skipping "{signal_name}" in "{category}": no usable data found.')
    return calibratables



def interpolate_threshold_clamped(table, x):
    """
    Linearly interpolate calibration thresholds for scalar or array x.
    Accepts:
      - dict with 'x'/'y' arrays
      - 2 x N array-like (first row x, second row y)
    Returns scalar if x is scalar, ndarray if x is array-like.
    """
    if table is None:
        raise ValueError("Calibration table is None")

    if isinstance(table, tuple) and len(table) == 2:
        x_vals = np.asarray(table[0], dtype=float)
        y_vals = np.asarray(table[1], dtype=float)
    elif isinstance(table, dict) and "x" in table and "y" in table:
        x_vals = np.asarray(table["x"], dtype=float)
        y_vals = np.asarray(table["y"], dtype=float)
    else:
        arr = np.asarray(table, dtype=float)
        if arr.ndim != 2 or arr.shape[0] != 2:
            raise ValueError(
                f"table must be 2 x N (two rows: breakpoints and values), got shape {arr.shape}"
            )
        x_vals, y_vals = arr[0], arr[1]

    if x_vals.shape != y_vals.shape:
        raise ValueError(
            f"Calibration table mismatch: x has {x_vals.shape} points, y has {y_vals.shape} points"
        )

    x_in = np.asarray(x, dtype=float)
    x_clamped = np.clip(x_in, np.min(x_vals), np.max(x_vals))
    result = np.interp(x_clamped, x_vals, y_vals)
    return float(result) if np.isscalar(x) or np.ndim(x_in) == 0 else result
