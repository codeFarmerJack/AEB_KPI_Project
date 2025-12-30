import warnings
from dataclasses import dataclass

import numpy as np

from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.event_detector.as_long.fcw import detect_fcw_events
from src.utils.data_utils import safe_scalar
from src.utils.kpis.as_long.fcw.brake_jerk import FcwBrakeJerkCalculator
from src.utils.kpis.as_long.fcw.fcw_warning import FcwWarningCalculator
from src.utils.signal_mdf import get_signal


# ------------------------------------------------------------------ #
# FCW KPI Extractor
# ------------------------------------------------------------------ #
class FcwEventKpiExtractor(BaseEventKpiExtractor):
    """
    FCW event KPIs with explicit criteria.

    Event detection:
    - First event per chunk: `fcwRequest` rises 0 -> 2 or 3
      (detect_fcw_events, merge_window=2.0s).

    KPI criteria:
    - logTime: start time of the first FCW event.
    - vehSpd: `egoSpeedKph` at logTime (nearest sample).
    - brakeJerkStart/End/Dur/Max/brakeAccelMin:
      * FCW trigger for jerk uses `fcwRequest` rising to >= 3.
      * Analyze `longActAccelFlt` in [t0 - 0.2, t0 + 1.0] s.
      * Mean speed within [brakejerk_min_speed, brakejerk_max_speed].
      * jerk < brakejerk_jerk_neg_thd starts, jerk > brakejerk_jerk_pos_thd ends.
      * Duration must satisfy 0 < dur <= 0.5 s.
    - fcwSensitivityLvl/fcwWarningTTC:
      * First `fcwRequest` rising edge where < 2 -> >= 2.
      * `fcwTTC` must satisfy 0 < TTC <= 10 at trigger.
    """

    FEATURE_NAME = "FCW"
    PARAM_SPECS = {
        "window_s":               {"default": 1.0,   "type": float, "desc": "Sliding window duration (s)"},
        "brakejerk_jerk_neg_thd": {"default": -20.0, "type": float, "desc": "Negative jerk threshold (m/s³)"},
        "brakejerk_jerk_pos_thd": {"default": 20.0,  "type": float, "desc": "Positive jerk threshold (m/s³)"},
        "brakejerk_min_speed":    {"default": 30.0,  "type": float, "desc": "Minimum valid speed (kph)"},
        "brakejerk_max_speed":    {"default": 130.0, "type": float, "desc": "Maximum valid speed (kph)"},
    }

    @dataclass(frozen=True)
    class _FcwSignals:
        time: np.ndarray
        accel: np.ndarray
        fcw_request: np.ndarray
        ego_speed: np.ndarray

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_fcw_chunks", feature_name="FCW")

        self.brake_jerk_calc = FcwBrakeJerkCalculator(self)
        self.fcw_warning_calc = FcwWarningCalculator(self)

    # ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single FCW MF4 file.
        Returns a dict of KPI values to write into kpi_table.
        """
        signals = self._load_signals(mdf, fname)
        if signals is None:
            return None

        fcw_start_time = self._detect_start_time(signals, fname)
        if fcw_start_time is None:
            return None

        result = {"logTime": safe_scalar(fcw_start_time)}
        result["vehSpd"] = self._vehicle_speed_at_time(signals, fcw_start_time)

        self._run_calculators(mdf, i)
        return result

    def _load_signals(self, mdf, fname):
        time = self._prepare_time(mdf)
        accel = get_signal(mdf, "longActAccelFlt")
        fcw_request = get_signal(mdf, "fcwRequest")
        ego_speed = get_signal(mdf, "egoSpeedKph")

        if accel is None or fcw_request is None:
            warnings.warn(f"⚠️ Missing accel or fcwRequest in {fname} → skipped.")
            return None

        return self._FcwSignals(
            time=time,
            accel=accel,
            fcw_request=fcw_request,
            ego_speed=ego_speed,
        )

    def _detect_start_time(self, signals, fname):
        try:
            start_times, _end_times = detect_fcw_events(signals.time, signals.fcw_request)
        except Exception as e:
            warnings.warn(f"[{fname}] detect_fcw_events failed: {e}")
            return None

        if len(start_times) == 0:
            warnings.warn(f"⚠️ No FCW events detected in {fname}")
            return None

        return start_times[0]

    def _vehicle_speed_at_time(self, signals, event_time):
        if signals.ego_speed is None:
            return np.nan
        start_idx = int(np.argmin(np.abs(signals.time - event_time)))
        return safe_scalar(signals.ego_speed[start_idx])

    def _run_calculators(self, mdf, index):
        self.brake_jerk_calc.compute_brake_jerk(mdf, self.kpi_table, index)
        self.fcw_warning_calc.compute_fcw_warning(mdf, self.kpi_table, index)
