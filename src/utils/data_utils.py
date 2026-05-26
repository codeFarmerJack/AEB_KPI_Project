import numpy as np
import pandas as pd
import warnings


def is_motion_1_source(signal_source) -> bool:
    """Return True when the configured input source is MOTION_1."""
    source_key = str(signal_source or "roadcast_log").strip().lower()
    return source_key in {"motion_1", "motion1"}


def prune_unsupported_columns_for_source(
    df: pd.DataFrame,
    signal_source,
    feature_name=None,
    table_kind="event",
    preserve_columns=("label", "feature"),
) -> pd.DataFrame:
    """
    For MOTION_1 exports, remove KPI columns that cannot be computed.

    Roadcast logs keep the complete configured schema because those KPIs can be
    captured there. MOTION_1 has a smaller signal set, but supported KPIs
    should remain even when an event does not occur in a particular recording.
    """
    if not is_motion_1_source(signal_source):
        return df
    if not isinstance(df, pd.DataFrame):
        return df

    out = df.copy()
    supported = _supported_motion_1_columns(feature_name, table_kind)
    if supported is None:
        return out

    preserved = [col for col in preserve_columns if col in out.columns]
    supported_cols = [col for col in out.columns if col in supported]
    keep = []
    for col in preserved + supported_cols:
        if col not in keep:
            keep.append(col)

    pruned = out.loc[:, keep]
    display_map = out.attrs.get("display_names", {}) or {}
    if display_map:
        pruned.attrs["display_names"] = {
            col: display_map.get(col, col)
            for col in pruned.columns
            if col in display_map
        }
    return pruned


def _supported_motion_1_columns(feature_name, table_kind):
    table = str(table_kind or "event").strip().lower()
    feature = str(feature_name or "").strip().upper()

    if table == "cycle":
        return {
            "label",
            "feature",
            "PedalPosProSuppression",
            "SteeringWheelAngle",
            "SteeringWheelAngleRate",
            "YawRate",
            "LatAccel",
            "LowSpeed",
        }

    common = {"label", "logTime", "vehSpd"}
    event_columns = {
        "AEB": {
            "aebIntvStartTime",
            "aebSysRespTime",
            "aebDeadTime",
            "aebIntvEndTime",
            "intvDur",
            "isVehStopped",
            "isPBOn",
            "isFBOn",
            "pbDur",
            "fbDur",
            "pedalPosAtStart",
            "isPedalOnAtStrt",
            "pedalPosMax",
            "pedalPosInc",
            "pedalPosIncTh",
            "isPedalPosIncHigh",
            "absSteerMaxDeg",
            "steerAngTh",
            "isSteerHigh",
            "absSteerRateMaxDeg",
            "steerAngRateTh",
            "isSteerAngRateHigh",
            "absLatAccelMax",
            "latAccelTh",
            "isLatAccelHigh",
            "absYawRateMaxDeg",
            "yawRateSuspTh",
            "isYawRateHigh",
            "commLatency",
            "aebAverageAccel",
            "brakeDistAeb",
        },
        "FCW": {
            "brakeJerkDur",
            "brakeJerkStart",
            "brakeJerkEnd",
            "brakeJerkMax",
            "brakeAccelMin",
        },
        "LSAEB": set(),
    }
    if feature not in event_columns:
        return None
    return common | event_columns[feature]


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
