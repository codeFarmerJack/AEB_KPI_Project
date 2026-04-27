import warnings
from dataclasses import dataclass

import numpy as np

from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.event_detector.as_long.lsaeb import detect_lsaeb_events
from src.utils.data_utils import safe_scalar
from src.utils.kpis.as_long.braking_average_accel import BrakingAverageAccelCalculator
from src.utils.kpis.as_long.braking_stop_distance import BrakingStopDistanceCalculator
from src.utils.kpis.as_long.lsaeb.distance import LsaebDistanceCalculator
from src.utils.signal_mdf import get_signal


# ------------------------------------------------------------------ #
# LSAEB KPI Extractor
# ------------------------------------------------------------------ #
class LsaebEventKpiExtractor(BaseEventKpiExtractor):
    """
    LSAEB event KPIs with explicit criteria.

    Event detection:
    - `cpmEventType` or `lsaeb_event_type` transitions 0 -> 1/2 start, 1/2 -> 0 end
      (detect_lsaeb_events, merge_window=2.0s). Uses the first event only.

    KPI criteria:
    - logTime: time at event start index.
    - vehSpd: `egoSpeedKph` at event start index.
    - lsaebIntvLongDist: `cpmLongDist` at event start index.
    - lsaebIntvLatDist: `cpmLatDist` at event start index.
    - lsaebStopLongDist: `cpmLongDist` at event end index.
    - lsaebStopLatDist: `cpmLatDist` at event end index.
    """

    FEATURE_NAME = "LSAEB"
    PARAM_SPECS = {
        "merge_window": {"default": 2.0, "type": float, "desc": "Event merge window (s)"},
    }

    @dataclass(frozen=True)
    class _LsaebSignals:
        time: np.ndarray
        ego_speed: np.ndarray
        event_type: np.ndarray

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_lsaeb_chunks", feature_name="LSAEB")
        self.distance_calc = LsaebDistanceCalculator(self)
        self.avg_accel_calc = BrakingAverageAccelCalculator(self)
        self.stop_distance_calc = BrakingStopDistanceCalculator(self)

    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single LSAEB MF4 file.
        Returns a dict of KPI values to write into kpi_table.
        """
        return self._extract_single_event_by_indices(mdf, fname, i)

    def _should_skip_event(self, signals, fname):
        return self._is_no_event(signals.event_type, fname)

    def _load_signals(self, mdf, fname):
        try:
            time = self._prepare_time(mdf)
            ego_speed = get_signal(mdf, "egoSpeedKph", required=True)
            event_type = self._get_event_type_signal(mdf)
        except AttributeError as e:
            warnings.warn(f"[{fname}] Missing required signal: {e}")
            return None

        return self._LsaebSignals(time=time, ego_speed=ego_speed, event_type=event_type)

    def _get_event_type_signal(self, mdf):
        for sig_name in ["cpmEventType", "lsaeb_event_type"]:
            event_type = get_signal(mdf, sig_name)
            if event_type is not None:
                return event_type
        raise AttributeError("Missing CPM event type signal (cpmEventType or lsaeb_event_type).")

    def _is_no_event(self, event_type, fname):
        if np.all(event_type == 0):
            warnings.warn(f"[{fname}] No LSAEB activation found (all zeros).")
            return True
        return False

    def _detect_events(self, signals, fname):
        try:
            start_indices, end_indices = detect_lsaeb_events(signals.time, signals.event_type)
        except Exception as e:
            warnings.warn(f"[{fname}] detect_lsaeb_events failed: {e}")
            return None

        if len(start_indices) == 0:
            warnings.warn(f"[{fname}] No LSAEB events detected.")
            return None

        return start_indices, end_indices

    def _build_event_result(self, signals, start_idx, end_idx):
        start_time = signals.time[start_idx]
        return {
            "logTime": safe_scalar(start_time),
            "vehSpd": safe_scalar(signals.ego_speed[start_idx]),
        }

    def _post_process_event_by_indices(self, mdf, index, signals, start_idx, end_idx, result):
        self.distance_calc.compute_distance(mdf, self.kpi_table, index, start_idx, end_idx)
        self.avg_accel_calc.compute_average_accel(
            mdf,
            self.kpi_table,
            index,
            "lsaebAverageAccel",
            min_speed_kph=2.0,
            max_speed_kph=10.0,
        )
        self.stop_distance_calc.compute_stop_distance(
            mdf,
            self.kpi_table,
            index,
            "brakeDistLsaeb",
        )
