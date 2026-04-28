import warnings

import numpy as np

from src.utils.event_detector.as_long.decel import detect_decel_onset


class ActualDecelOnsetResolver:
    """Resolve the onset of actual deceleration after the braking request edge."""

    def __init__(self, extractor):
        self.extractor = extractor

    def resolve_start_idx(
        self,
        time,
        accel_for_onset,
        request_start_idx,
        *,
        end_idx,
        row_idx,
        column_name,
        fallback_label="target decel edge",
    ):
        onset_threshold = float(getattr(self.extractor, "aeb_jerk_neg_thd", -20.0))
        search_end_idx = min(
            end_idx,
            request_start_idx + int(getattr(self.extractor, "latency_window_samples", 30)),
        )
        if search_end_idx <= request_start_idx:
            return request_start_idx

        accel_window = np.asarray(accel_for_onset[request_start_idx : search_end_idx + 1], dtype=float)
        time_window = np.asarray(time[request_start_idx : search_end_idx + 1], dtype=float)
        finite_mask = np.isfinite(accel_window) & np.isfinite(time_window)
        if np.count_nonzero(finite_mask) < 2:
            return request_start_idx

        accel_window = accel_window[finite_mask]
        time_window = time_window[finite_mask]
        if np.any(np.diff(time_window) <= 0):
            warnings.warn(
                f"[Row {row_idx}] {column_name}: non-monotonic time vector while detecting actual decel onset; "
                f"falling back to {fallback_label}"
            )
            return request_start_idx

        jerk = np.gradient(accel_window, time_window)
        onset_rel_idx = detect_decel_onset(jerk, onset_threshold)
        if onset_rel_idx is None:
            warnings.warn(
                f"[Row {row_idx}] {column_name}: no actual decel onset detected; "
                f"falling back to {fallback_label}"
            )
            return request_start_idx

        onset_time = time_window[onset_rel_idx]
        actual_idx = np.searchsorted(time, onset_time, side="left")
        return int(max(request_start_idx, min(actual_idx, end_idx)))
