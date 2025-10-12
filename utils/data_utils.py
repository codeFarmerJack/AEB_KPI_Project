# ====================================================================== #
# Shared utility functions used across multiple KPI features (AEB, FCW…)
# ====================================================================== #

import numpy as np
import pandas as pd
import warnings


# ------------------------------------------------------------------ #
# Utility: Safe conversion to scalar
# ------------------------------------------------------------------ #
def safe_scalar(x):
    """
    Convert array-like or irregular values into a scalar float or NaN.

    This ensures consistent numeric values when extracting single elements
    from NumPy arrays, pandas Series, or lists — particularly useful for
    populating KPI tables or exporting to Excel.

    Parameters
    ----------
    x : any
        The input value (scalar, list, ndarray, Series, None, etc.)

    Returns
    -------
    float
        A scalar float value or np.nan if conversion fails.

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
    if x is None:
        return np.nan
    if isinstance(x, (list, np.ndarray, pd.Series)):
        if len(x) == 0:
            return np.nan
        return float(np.ravel(x)[0])
    try:
        return float(x)
    except Exception:
        warnings.warn(f"⚠️ safe_scalar: could not convert {x!r} to float.")
        return np.nan
