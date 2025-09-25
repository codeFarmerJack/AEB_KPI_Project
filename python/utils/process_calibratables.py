def extract_calibratables(cal_struct):
    """
    Flattens nested calibratable dict and extracts `.Data` fields.

    Parameters
    ----------
    cal_struct : dict
        Nested dict with categories and signals.
        Example:
        {
            "steering": {
                "angle": {"Data": [..]},
                "torque": {"Data": [..]}
            },
            "throttle": {
                "position": {"Data": [..]}
            }
        }

    Returns
    -------
    calibratables : dict
        Flat dict {signal_name: data_array}.
    """
    calibratables = {}

    for category, category_struct in cal_struct.items():
        for signal_name, signal_struct in category_struct.items():
            if isinstance(signal_struct, dict) and "Data" in signal_struct:
                calibratables[signal_name] = signal_struct["Data"]
            else:
                # In MATLAB it prints a warning, here we log
                print(f'⚠️ Skipping "{signal_name}" in "{category}": no .Data field found.')

    return calibratables


def interpolate_threshold_clamped(table, x_query):
    """
    Interpolate from a 2-row calibratable table with clamping.

    Parameters
    ----------
    table : array-like (2 x N)
        Row 0 = input breakpoints (x values),
        Row 1 = corresponding threshold values (y values).
    x_query : float
        Scalar input value to interpolate.

    Returns
    -------
    y : float
        Interpolated or clamped threshold value.
    """
    table = np.asarray(table)
    if table.shape[0] != 2:
        raise ValueError("table must be 2 x N (two rows: breakpoints and values)")

    x_table = table[0, :]
    y_table = table[1, :]

    # Clamp query into the table’s range
    x_clamped = np.clip(x_query, np.min(x_table), np.max(x_table))

    # Linear interpolation
    y = np.interp(x_clamped, x_table, y_table)

    return float(y)