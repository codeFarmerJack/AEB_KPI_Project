import warnings
from dataclasses import dataclass

import numpy as np

from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.event_detector.as_long.lsaeb import detect_lsaeb_events
from src.utils.data_utils import safe_scalar
from src.utils.kpis.as_long.lsaeb.distance import LsaebDistanceCalculator
from src.utils.signal_mdf import get_signal


# ------------------------------------------------------------------ #
# LSAEB KPI Extractor
# ------------------------------------------------------------------ #
class LsaebEventKpiExtractor(BaseEventKpiExtractor):
    """Extracts LSAEB KPI metrics from MF4 chunks (distance + timing)."""

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


    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single LSAEB MF4 file.
        Returns a dict of KPI values to write into kpi_table.
        """
        signals = self._load_signals(mdf, fname)
        if signals is None:
            return None

        signals = self._align_signals(signals, fname)
        if self._is_no_event(signals.event_type, fname):
            return None

        event_indices = self._detect_events(signals, fname)
        if event_indices is None:
            return None

        start_idx, end_idx = self._select_event_indices(event_indices, len(signals.time))
        result = self._build_event_result(signals, start_idx)

        self.distance_calc.compute_distance(mdf, self.kpi_table, i, start_idx, end_idx)
        return result

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

    def _align_signals(self, signals, fname):
        if len(signals.time) == len(signals.event_type):
            return signals

        n = min(len(signals.time), len(signals.event_type))
        warnings.warn(f"[{fname}] Signal length mismatch — trimming to {n} samples.")
        return self._LsaebSignals(
            time=signals.time[:n],
            ego_speed=signals.ego_speed[:n],
            event_type=signals.event_type[:n],
        )

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

    def _select_event_indices(self, event_indices, n_samples):
        start_indices, end_indices = event_indices
        start_idx = int(start_indices[0])
        end_idx = int(end_indices[0]) if len(end_indices) > 0 else n_samples - 1

        start_idx = max(0, min(start_idx, n_samples - 1))
        end_idx = max(0, min(end_idx, n_samples - 1))
        return start_idx, end_idx

    def _build_event_result(self, signals, start_idx):
        start_time = signals.time[start_idx]
        return {
            "logTime": safe_scalar(start_time),
            "vehSpd": safe_scalar(signals.ego_speed[start_idx]),
        }
