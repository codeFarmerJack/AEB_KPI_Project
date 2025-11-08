import os
import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass
from pipeline.base.base_kpi_extractor import BaseKpiExtractor
from utils.event_detector.as_long.lsaeb import detect_lsaeb_events
from utils.data_utils import safe_scalar
from utils.kpis.as_long.lsaeb.distance import LsaebDistanceCalculator


# ------------------------------------------------------------------ #
# LSAEB KPI Extractor
# ------------------------------------------------------------------ #
class LsaebKpiExtractor(BaseKpiExtractor):
    """Extracts LSAEB KPI metrics from MF4 chunks (distance + timing)."""

    FEATURE_NAME = "LSAEB"
    PARAM_SPECS = {
        "merge_window": {"default": 2.0, "type": float, "desc": "Event merge window (s)"},
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_detector):
        super().__init__(config, event_detector, "in_path_lsaeb_chunks", feature_name="LSAEB")
        self.distance_calc = LsaebDistanceCalculator(self)

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all LSAEB MF4 chunk files and extract KPI metrics."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.out_path_chunks, fname)
            self._insert_label(i, fname)
            print(f"\n📊 Processing LSAEB KPI for file {i + 1}/{len(self.file_list)}: {fname}")

            # --- Load MDF segment ---
            mdf = self._load_mdf(fpath)
            if mdf is None:
                continue

            # --- Extract signals (segment-level) ---
            try:
                time = self._prepare_time(mdf)
                ego_speed = np.asarray(mdf.egoSpeedKph)

                # Try to get event-type signal from segment
                if hasattr(mdf, "cpmEventType"):
                    lsaeb_event_type = np.asarray(mdf.cpmEventType)
                elif hasattr(mdf, "lsaeb_event_type"):
                    lsaeb_event_type = np.asarray(mdf.lsaeb_event_type)
                else:
                    raise AttributeError("Missing CPM event type signal (cpmEventType or lsaeb_event_type).")

            except AttributeError as e:
                warnings.warn(f"[Row {i}] Missing required signal: {e}")
                continue

            # --- Basic sanity check ---
            if len(time) != len(lsaeb_event_type):
                n = min(len(time), len(lsaeb_event_type))
                warnings.warn(f"[Row {i}] Signal length mismatch — trimming to {n} samples.")
                time = time[:n]
                ego_speed = ego_speed[:n]
                lsaeb_event_type = lsaeb_event_type[:n]

            if np.all(lsaeb_event_type == 0):
                warnings.warn(f"[Row {i}] No LSAEB activation found (all zeros).")
                continue

            # --- Detect events *inside this segment* ---
            try:
                start_indices, end_indices = detect_lsaeb_events(time, lsaeb_event_type)
            except Exception as e:
                warnings.warn(f"[Row {i}] detect_lsaeb_events failed: {e}")
                continue

            if len(start_indices) == 0:
                warnings.warn(f"[Row {i}] No LSAEB events detected.")
                continue

            # --- Use first event (you can extend to loop through all later) ---
            lsaeb_start_idx = int(start_indices[0])
            lsaeb_end_idx = int(end_indices[0]) if len(end_indices) > 0 else len(time) - 1

            # --- Clip indices safely within segment length ---
            lsaeb_start_idx = max(0, min(lsaeb_start_idx, len(time) - 1))
            lsaeb_end_idx = max(0, min(lsaeb_end_idx, len(time) - 1))

            # --- Derive timing ---
            lsaeb_start_time = time[lsaeb_start_idx]

            # --- Save timing info ---
            self.kpi_table.loc[i, "logTime"] = safe_scalar(lsaeb_start_time)

            # --- Vehicle speed at start ---
            veh_spd = safe_scalar(ego_speed[lsaeb_start_idx])
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- Compute distance KPIs ---
            self.distance_calc.compute_distance(mdf, self.kpi_table, i, lsaeb_start_idx, lsaeb_end_idx)

            # --- Round and finalize ---
            self.kpi_table = self.kpi_table.round(3)

        print("\n✅ LSAEB KPI extraction completed successfully.")
