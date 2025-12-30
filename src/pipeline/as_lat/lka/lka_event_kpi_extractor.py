import warnings
from dataclasses import dataclass

import numpy as np

from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.data_utils import safe_scalar
from src.utils.event_detector.as_lat.lka import detect_lka_events  
from src.utils.signal_mdf import get_signal


# ------------------------------------------------------------------ #
# LKA KPI Extractor
# ------------------------------------------------------------------ #
class LkaEventKpiExtractor(BaseEventKpiExtractor):
    """
    LKA event KPIs with explicit criteria.

    Event detection:
    - `lkaInterventionStatus` rising 0 -> 1 starts, falling 1 -> 0 ends
      (detect_lka_events). Uses the first event only.

    KPI criteria:
    - logTime: time at event start index.
    - MinDTLEDelta: `dtleTarget` at start minus min `dtle` in [start, end].
    - TrigDTLE: `dtle` at start.
    - isWhlTrqHigh: any |steerWheelTorque| > driver_interaction_torque in [start, end].
    - TrigRateOfDeparture: `rateOfDeparture` at start.
    - TrigVehCurv: `vehCurvature` at start.
    - TrigLaneCurv: `laneCurvature` at start.
    - vehSpd: `egoSpeedKph` at start (if present, else NaN).
    - UseCase: `useCase` at start (if present, else NaN).
    """

    FEATURE_NAME = "LKA"
    PARAM_SPECS = {
        "driver_interaction_torque": {
            "default": 2.0,
            "type": float,
            "desc": "Threshold for driver interaction torque [Nm]",
        },
    }

    @dataclass(frozen=True)
    class _LkaSignals:
        time: np.ndarray
        dtle: np.ndarray
        dtle_target: np.ndarray
        lka_status: np.ndarray
        steer_torque: np.ndarray
        rate_of_departure: np.ndarray
        veh_curvature: np.ndarray
        lane_curvature: np.ndarray
        use_case: np.ndarray
        ego_speed: np.ndarray

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_lka_chunks", feature_name="LKA")
        self.driver_torque_th = float(getattr(self, "driver_interaction_torque", 2.0))

    # ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single LKA event segment.
        Returns a dict of KPI values to write into kpi_table.
        """
        signals = self._load_signals(mdf, fname)
        if signals is None:
            return None

        signals = self._align_signals(signals, fname)
        event_indices = self._detect_events(signals, fname)
        if event_indices is None:
            return None

        start_idx, end_idx = self._select_event_indices(event_indices, len(signals.time))
        return self._build_event_result(signals, start_idx, end_idx)

    def _load_signals(self, mdf, fname):
        try:
            time = self._prepare_time(mdf)
            dtle = get_signal(mdf, "dtle", required=True)
            lka_status = get_signal(mdf, "lkaInterventionStatus", required=True)
            steer_torque = get_signal(mdf, "steerWheelTorque", required=True)
            rate_of_departure = get_signal(mdf, "rateOfDeparture", required=True)
            veh_curvature = get_signal(mdf, "vehCurvature", required=True)
            lane_curvature = get_signal(mdf, "laneCurvature", required=True)
        except AttributeError as e:
            warnings.warn(f"[{fname}] Missing required signal: {e}")
            return None

        dtle_target = get_signal(mdf, "dtleTarget", default=np.full_like(dtle, np.nan))
        use_case = get_signal(mdf, "useCase", default=np.full_like(dtle, np.nan))
        ego_speed = get_signal(mdf, "egoSpeedKph", default=np.full_like(dtle, np.nan))

        return self._LkaSignals(
            time=time,
            dtle=dtle,
            dtle_target=dtle_target,
            lka_status=lka_status,
            steer_torque=steer_torque,
            rate_of_departure=rate_of_departure,
            veh_curvature=veh_curvature,
            lane_curvature=lane_curvature,
            use_case=use_case,
            ego_speed=ego_speed,
        )

    def _align_signals(self, signals, fname):
        lengths = [
            len(signals.time),
            len(signals.dtle),
            len(signals.lka_status),
            len(signals.steer_torque),
            len(signals.rate_of_departure),
            len(signals.veh_curvature),
            len(signals.lane_curvature),
            len(signals.dtle_target),
            len(signals.use_case),
            len(signals.ego_speed),
        ]
        min_len = min(lengths)
        if all(length == min_len for length in lengths):
            return signals

        warnings.warn(f"[{fname}] Signal length mismatch — trimming to {min_len} samples.")
        return self._LkaSignals(
            time=signals.time[:min_len],
            dtle=signals.dtle[:min_len],
            dtle_target=signals.dtle_target[:min_len],
            lka_status=signals.lka_status[:min_len],
            steer_torque=signals.steer_torque[:min_len],
            rate_of_departure=signals.rate_of_departure[:min_len],
            veh_curvature=signals.veh_curvature[:min_len],
            lane_curvature=signals.lane_curvature[:min_len],
            use_case=signals.use_case[:min_len],
            ego_speed=signals.ego_speed[:min_len],
        )

    def _detect_events(self, signals, fname):
        try:
            start_indices, end_indices = detect_lka_events(signals.time, signals.lka_status)
        except Exception as e:
            warnings.warn(f"[{fname}] detect_lka_events failed: {e}")
            return None

        if len(start_indices) == 0:
            warnings.warn(f"[{fname}] No LKA events detected.")
            return None

        return start_indices, end_indices

    def _select_event_indices(self, event_indices, n_samples):
        start_indices, end_indices = event_indices
        start_idx = int(start_indices[0])
        end_idx = int(end_indices[0]) if len(end_indices) else n_samples - 1

        start_idx = max(0, min(start_idx, n_samples - 1))
        end_idx = max(0, min(end_idx, n_samples - 1))
        return start_idx, end_idx

    def _build_event_result(self, signals, start_idx, end_idx):
        dtle_target_at_start = safe_scalar(signals.dtle_target[start_idx])
        dtle_at_start = safe_scalar(signals.dtle[start_idx])
        dtle_min_during = np.nanmin(signals.dtle[start_idx:end_idx + 1])
        min_dtle_delta = safe_scalar(dtle_target_at_start - dtle_min_during)

        is_high = self._is_torque_high(signals.steer_torque, start_idx, end_idx)

        return {
            "logTime": safe_scalar(signals.time[start_idx]),
            "MinDTLEDelta": min_dtle_delta,
            "TrigDTLE": dtle_at_start,
            "isWhlTrqHigh": bool(is_high),
            "TrigRateOfDeparture": safe_scalar(signals.rate_of_departure[start_idx]),
            "TrigVehCurv": safe_scalar(signals.veh_curvature[start_idx]),
            "TrigLaneCurv": safe_scalar(signals.lane_curvature[start_idx]),
            "vehSpd": safe_scalar(signals.ego_speed[start_idx]),
            "UseCase": safe_scalar(signals.use_case[start_idx]),
        }

    def _is_torque_high(self, steer_torque, start_idx, end_idx):
        window = steer_torque[start_idx:end_idx + 1]
        return np.any(np.abs(window) > self.driver_torque_th)
