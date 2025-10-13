import numpy as np
import pandas as pd
import warnings

def safe_scalar(x, warn: bool = True):
    """
    Safely convert any scalar, list, NumPy array, or pandas object into a float scalar or NaN.

    This unifies safe_scalar() and safe_float() functionality.

    Parameters
    ----------
    x : any
        Input value — scalar, list, ndarray, Series, or None.
    warn : bool, optional
        If True (default), emits a warning on failed conversion.

    Returns
    -------
    float
        A float value or np.nan if conversion is not possible.

    Examples
    --------
    >>> safe_scalar([12.3])
    12.3
    >>> safe_scalar(np.array([5.0]))
    5.0
    >>> safe_scalar(None)
    nan
    >>> safe_scalar("3.14")
    3.14
    >>> safe_scalar("abc")
    nan
    """
    # 1️⃣ Handle None or empty input
    if x is None:
        return np.nan
    if isinstance(x, (list, np.ndarray, pd.Series)):
        if len(x) == 0:
            return np.nan
        # Flatten & recurse on first element
        return safe_scalar(np.ravel(x)[0], warn=warn)

    # 2️⃣ Handle numeric and NaN values
    if isinstance(x, (int, float, np.floating, np.integer)):
        return np.nan if np.isnan(x) else float(x)

    # 3️⃣ Try to convert strings like "3.14"
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            if warn:
                warnings.warn(f"⚠️ safe_scalar: could not convert string '{x}' to float.")
            return np.nan

    # 4️⃣ Fallback for unsupported types
    try:
        return float(x)
    except Exception:
        if warn:
            warnings.warn(f"⚠️ safe_scalar: could not convert {x!r} to float.")
        return np.nan
