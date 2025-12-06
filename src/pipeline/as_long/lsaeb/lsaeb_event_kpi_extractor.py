import numpy as np
import warnings
from src.pipeline.base.base_event_kpi_extractor import BaseEventKpiExtractor
from src.utils.event_detector.as_long.lsaeb import detect_lsaeb_events
from src.utils.data_utils import safe_scalar
from src.utils.kpis.as_long.lsaeb.distance import LsaebDistanceCalculator


# ------------------------------------------------------------------ #
# LSAEB KPI Extractor
# ------------------------------------------------------------------ #
class LsaebEventKpiExtractor(BaseEventKpiExtractor):
    """Extracts LSAEB KPI metrics from MF4 chunks (distance + timing)."""

    FEATURE_NAME = "LSAEB"
    PARAM_SPECS = {
        "merge_window": {"default": 2.0, "type": float, "desc": "Event merge window (s)"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_lsaeb_chunks", feature_name="LSAEB")
        self.distance_calc = LsaebDistanceCalculator(self)


    def extract_event_kpis(self, mdf, fname, i):
        """
        Extract KPI values for a single LSAEB MF4 file.
        Returns a dict of KPI values to write into kpi_table.
        """

        result = {}

        # --- Extract signals ---
        try:
            time = self._prepare_time(mdf)
            ego_speed = np.asarray(mdf.egoSpeedKph)

            # Event-type signal
            if hasattr(mdf, "cpmEventType"):
                lsaeb_event_type = np.asarray(mdf.cpmEventType)
            elif hasattr(mdf, "lsaeb_event_type"):
                lsaeb_event_type = np.asarray(mdf.lsaeb_event_type)
            else:
                raise AttributeError("Missing CPM event type signal (cpmEventType or lsaeb_event_type).")

        except AttributeError as e:
            warnings.warn(f"[{fname}] Missing required signal: {e}")
            return None

        # --- Length mismatch trimming ---
        if len(time) != len(lsaeb_event_type):
            n = min(len(time), len(lsaeb_event_type))
            warnings.warn(f"[{fname}] Signal length mismatch — trimming to {n} samples.")
            time = time[:n]
            ego_speed = ego_speed[:n]
            lsaeb_event_type = lsaeb_event_type[:n]

        # --- No event found ---
        if np.all(lsaeb_event_type == 0):
            warnings.warn(f"[{fname}] No LSAEB activation found (all zeros).")
            return None

        # --- Detect events ---
        try:
            start_indices, end_indices = detect_lsaeb_events(time, lsaeb_event_type)
        except Exception as e:
            warnings.warn(f"[{fname}] detect_lsaeb_events failed: {e}")
            return None

        if len(start_indices) == 0:
            warnings.warn(f"[{fname}] No LSAEB events detected.")
            return None

        # Use 1st event
        start_idx = int(start_indices[0])
        end_idx = int(end_indices[0]) if len(end_indices) > 0 else len(time) - 1

        # Clip safely
        start_idx = max(0, min(start_idx, len(time) - 1))
        end_idx = max(0, min(end_idx, len(time) - 1))

        # --- Timing KPI ---
        start_time = time[start_idx]
        result["logTime"] = safe_scalar(start_time)

        # --- Veh speed at event start ---
        veh_spd = safe_scalar(ego_speed[start_idx])
        result["vehSpd"] = veh_spd

        # --- Distance KPIs (write directly into table via calculator API) ---
        self.distance_calc.compute_distance(mdf, self.kpi_table, i, start_idx, end_idx)

        return result