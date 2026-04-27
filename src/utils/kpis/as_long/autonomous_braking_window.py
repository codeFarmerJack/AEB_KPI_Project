import warnings
from dataclasses import dataclass

import numpy as np

from src.utils.signal_mdf import get_signal


@dataclass(frozen=True)
class AutonomousBrakingWindow:
    time: np.ndarray
    target_decel: np.ndarray
    brake_pedal: np.ndarray | None
    ego_speed_kph: np.ndarray | None
    ego_speed_mps: np.ndarray | None
    start_idx: int
    stop_idx: int


class AutonomousBrakingWindowResolver:
    """Resolve the autonomous-braking window from target-decel edge to vehicle stop."""

    def __init__(self, extractor):
        self.extractor = extractor

    def resolve(
        self,
        mdf,
        *,
        row_idx,
        column_name,
        require_brake_pedal_released=False,
        require_speed_kph=False,
        require_speed_mps=False,
        stop_signal="ego_speed_mps",
        stop_mode="isclose",
        stop_value=0.0,
        stop_tolerance=1e-6,
    ):
        time = get_signal(mdf, "time")
        if time is None and hasattr(self.extractor, "_prepare_time"):
            time = self.extractor._prepare_time(mdf)

        target_decel = get_signal(mdf, "aebTargetDecel")
        brake_pedal = get_signal(mdf, "brakePedalPressed") if require_brake_pedal_released else None
        ego_speed_kph = get_signal(mdf, "egoSpeedKph")
        ego_speed_mps = get_signal(mdf, "egoSpeed")

        if ego_speed_mps is None and ego_speed_kph is not None:
            ego_speed_mps = np.asarray(ego_speed_kph, dtype=float) / 3.6
        if ego_speed_kph is None and ego_speed_mps is not None:
            ego_speed_kph = np.asarray(ego_speed_mps, dtype=float) * 3.6

        required = {
            "time": time,
            "aebTargetDecel": target_decel,
        }
        if require_brake_pedal_released:
            required["brakePedalPressed"] = brake_pedal
        if require_speed_kph:
            required["egoSpeedKph"] = ego_speed_kph
        if require_speed_mps:
            required["egoSpeed"] = ego_speed_mps

        missing = [name for name, signal in required.items() if signal is None]
        if missing:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: missing required signal(s): {', '.join(missing)}"
            )
            return None

        arrays = [signal for signal in (time, target_decel, brake_pedal, ego_speed_kph, ego_speed_mps) if signal is not None]
        min_len = min(len(signal) for signal in arrays)
        if min_len < 1:
            warnings.warn(f"[Row {row_idx}] {column_name}: insufficient samples (min_len={min_len})")
            return None

        time = np.asarray(time[:min_len], dtype=float)
        target_decel = np.asarray(target_decel[:min_len], dtype=float)
        brake_pedal = None if brake_pedal is None else np.asarray(brake_pedal[:min_len], dtype=float)
        ego_speed_kph = None if ego_speed_kph is None else np.asarray(ego_speed_kph[:min_len], dtype=float)
        ego_speed_mps = None if ego_speed_mps is None else np.asarray(ego_speed_mps[:min_len], dtype=float)

        start_idx = self.find_start_idx(
            target_decel,
            brake_pedal=brake_pedal,
            require_brake_pedal_released=require_brake_pedal_released,
        )
        if start_idx is None:
            qualifier = " with brakePedalPressed == 0" if require_brake_pedal_released else ""
            warnings.warn(
                f"[Row {row_idx}] {column_name}: no aebTargetDecel falling edge found{qualifier}"
            )
            return None

        stop_speed = {
            "ego_speed_kph": ego_speed_kph,
            "ego_speed_mps": ego_speed_mps,
        }.get(stop_signal)
        if stop_speed is None:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: stop signal '{stop_signal}' is unavailable"
            )
            return None

        stop_idx = self.find_stop_idx(
            stop_speed,
            start_idx,
            mode=stop_mode,
            value=stop_value,
            tolerance=stop_tolerance,
        )
        if stop_idx is None:
            comparator = "<" if stop_mode == "lt" else "="
            warnings.warn(
                f"[Row {row_idx}] {column_name}: vehicle never reached {stop_signal} {comparator} {stop_value}"
            )
            return None

        return AutonomousBrakingWindow(
            time=time,
            target_decel=target_decel,
            brake_pedal=brake_pedal,
            ego_speed_kph=ego_speed_kph,
            ego_speed_mps=ego_speed_mps,
            start_idx=start_idx,
            stop_idx=stop_idx,
        )

    @staticmethod
    def find_start_idx(target_decel, *, brake_pedal=None, require_brake_pedal_released=False):
        falling_edge = (target_decel[:-1] >= 0.0) & (target_decel[1:] < 0.0)
        if require_brake_pedal_released:
            if brake_pedal is None:
                return None
            pedal_not_pressed = np.isclose(brake_pedal[1:], 0.0, atol=1e-6)
            falling_edge &= pedal_not_pressed

        candidates = np.flatnonzero(falling_edge)
        if candidates.size == 0:
            return None
        return int(candidates[0] + 1)

    @staticmethod
    def find_stop_idx(speed, start_idx, *, mode, value, tolerance):
        speed_slice = np.asarray(speed[start_idx:], dtype=float)
        finite_mask = np.isfinite(speed_slice)
        if not np.any(finite_mask):
            return None

        if mode == "lt":
            stop_mask = finite_mask & (speed_slice < value)
        elif mode == "isclose":
            stop_mask = finite_mask & np.isclose(speed_slice, value, atol=tolerance)
        else:
            raise ValueError(f"Unsupported stop mode '{mode}'")

        stop_candidates = np.flatnonzero(stop_mask)
        if stop_candidates.size == 0:
            return None
        return int(start_idx + stop_candidates[0])
