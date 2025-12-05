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
    if isinstance(table, dict) and "x" in table and "y" in table:
        x_arr = np.asarray(table["x"], dtype=float)
        y_arr = np.asarray(table["y"], dtype=float)

        if len(x_arr) != len(y_arr):
            raise ValueError(
                f"Calibration table mismatch: x has {len(x_arr)} points, y has {len(y_arr)} points"
            )

        table = np.vstack([x_arr, y_arr])
    else:
        table = np.asarray(table, dtype=float)

    if table.shape[0] != 2:
        raise ValueError(
            f"table must be 2 x N (two rows: breakpoints and values), got shape {table.shape}"
        )

    x_vals, y_vals = table[0], table[1]
    x_clamped = np.clip(x, np.min(x_vals), np.max(x_vals))
    return float(np.interp(x_clamped, x_vals, y_vals))

