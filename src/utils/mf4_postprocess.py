import warnings

import numpy as np
import pandas as pd
from asammdf import Signal

from src.utils.signal_filters import accel_filter

FILTER_SIGNALS = ("longActAccel", "latActAccel")
CONVERSIONS = {
    "egoSpeed": ("egoSpeedKph", lambda x: x * 3.6, "m/s -> km/h"),
    "objSpeed": ("objSpeedKph", lambda x: x * 3.6, "m/s -> km/h"),
    "steerWheelAngle": ("steerWheelAngleDeg", np.degrees, "rad -> deg"),
    "steerWheelAngleSpeed": ("steerWheelAngleSpeedDeg", np.degrees, "rad/s -> deg/s"),
    "yawRate": ("yawRateDeg", np.degrees, "rad/s -> deg/s"),
}

MOTION_1_UNIT_NORMALIZERS = {
    "egoSpeed": lambda x: x / 3.6,
    "steerWheelAngle": np.radians,
    "steerWheelAngleSpeed": np.radians,
    "yawRate": np.radians,
}


def apply_filters(data, cutoff_freq, signals=FILTER_SIGNALS):
    if data is None or data.empty:
        return pd.DataFrame(index=getattr(data, "index", None))

    derived = {}
    for sig in signals:
        if sig not in data.columns:
            warnings.warn(f"⚠️ Signal '{sig}' not found in extracted data.")
            continue

        try:
            sig_flt = accel_filter(
                data.index.values,
                data[sig].values,
                cutoff_freq=cutoff_freq,
            )
            derived[f"{sig}Flt"] = sig_flt
            print(f"   ✅ Filtered signal: {sig} → {sig}Flt")
        except Exception as e:
            warnings.warn(f"⚠️ Failed to filter {sig}: {e}")

    return pd.DataFrame(derived, index=data.index)


def apply_conversions(data, conversions=CONVERSIONS):
    if data is None or data.empty:
        return pd.DataFrame(index=getattr(data, "index", None))

    derived = {}
    for src, (dst, func, desc) in conversions.items():
        if src not in data.columns:
            warnings.warn(f"⚠️ Signal '{src}' not found in extracted data.")
            continue

        try:
            derived[dst] = func(data[src])
            print(f"   ✅ Converted {src} → {dst} ({desc})")
        except Exception as e:
            warnings.warn(f"⚠️ Failed to convert {src}: {e}")

    return pd.DataFrame(derived, index=data.index)


def postprocess_signals(data, cutoff_freq):
    if data is None or data.empty:
        return pd.DataFrame(index=getattr(data, "index", None))

    derived = pd.DataFrame(index=data.index)
    for df in (apply_filters(data, cutoff_freq), apply_conversions(data)):
        if df is not None and not df.empty:
            derived = derived.join(df, how="outer")
    return derived


def normalize_source_signals(data, signal_source):
    if data is None or data.empty:
        return data

    source_key = str(signal_source or "roadcast_log").strip().lower()
    if source_key not in {"motion_1", "motion1"}:
        return data

    normalized = data.copy()
    for signal_name, func in MOTION_1_UNIT_NORMALIZERS.items():
        if signal_name in normalized.columns:
            normalized[signal_name] = func(normalized[signal_name].astype(float))
            print(f"   ✅ Normalized MOTION_1 {signal_name} into KPI base units")

    if "aebTargetDecel" in normalized.columns:
        target_decel = normalized["aebTargetDecel"].astype(float)
        normalized["aebRequest"] = np.select(
            [
                np.isclose(target_decel, -6.0),
                np.isclose(target_decel, -11.0),
                np.isclose(target_decel, -5.0),
            ],
            [1, 2, 3],
            default=0,
        )
        normalized["aebPartialState"] = np.where(np.isclose(target_decel, -6.0), 2, 1)
        normalized["aebFullState"] = np.where(
            np.isclose(target_decel, -11.0) | np.isclose(target_decel, -5.0),
            2,
            1,
        )
        print("   ✅ Derived MOTION_1 AEB request/state signals from DADCAxLmtIT4")

    if "fcwState" in normalized.columns:
        fcw_state = normalized["fcwState"].astype(float)
        normalized["fcwRequest"] = np.where(fcw_state == 5, 3, 0)
        print("   ✅ Derived MOTION_1 fcwRequest from FCWState")

    return normalized


def merge_signals(raw, derived):
    if raw is None:
        return derived
    if derived is None or derived.empty:
        return raw

    merged = raw.copy()
    for col in derived.columns:
        merged[col] = derived[col]
    return merged


def build_signal(name, series, enum_mapper):
    if series.dtype == object:
        enum_name = enum_mapper.get_enum_for_signal(name)

        if enum_name:
            enum_table = enum_mapper.enums.get(enum_name, {})
            encoded = series.astype(str).map(enum_table)
            if encoded.isna().any():
                missing = series[encoded.isna()].unique().tolist()
                print(f"⚠️ Unmapped values in {name}: {missing}")
            samples = encoded.fillna(-1).astype(np.int16).to_numpy()
            return Signal(
                samples=samples,
                timestamps=series.index.values,
                name=name,
                unit="u[1]",
                comment=f"Enum mapping: {enum_name}",
            )

        categories, encoded = np.unique(series.astype(str), return_inverse=True)
        return Signal(
            samples=encoded.astype(np.int16),
            timestamps=series.index.values,
            name=name,
            unit="u[1]",
            comment=f"Categorical mapping: {dict(enumerate(categories))}",
        )

    return Signal(
        samples=series.to_numpy(dtype=np.float64),
        timestamps=series.index.values,
        name=name,
        unit="u[1]",
    )
