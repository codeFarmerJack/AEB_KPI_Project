import os
import numpy as np
import pandas as pd
import warnings
from dataclasses import dataclass
from pipeline.base.base_kpi_extractor import BaseKpiExtractor
from utils.data_utils import safe_scalar
from utils.event_detector.as_lat.lka import detect_lka_events  


# ------------------------------------------------------------------ #
# LKA KPI Extractor
# ------------------------------------------------------------------ #
class LkaKpiExtractor(BaseKpiExtractor):
    """Extracts LKA (Lane Keeping Assist) KPI metrics."""

    FEATURE_NAME = "LKA"
    PARAM_SPECS = {
        "Driver_Interaction_Torque": {
            "default": 2.0,
            "type": float,
            "desc": "Threshold for driver interaction torque [Nm]",
        },
    }

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_detector=None):
        super().__init__(config, event_detector, "in_path_lka_chunks", feature_name="LKA")
        self.driver_torque_th = float(config.params.get("driver_interaction_torque", 2.0))

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all LKA MF4 chunk files and extract KPI metrics."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.out_path_chunks, fname)
            self._insert_label(i, fname)
            print(f"\n📊 Processing LKA KPI for file {i + 1}/{len(self.file_list)}: {fname}")

            # --- Load MDF segment ---
            mdf = self._load_mdf(fpath)
            if mdf is None:
                continue

            # --- Extract signals ---
            try:
                time = self._prepare_time(mdf)
                dtle = np.asarray(mdf.dtle)
                dtle_target = np.asarray(getattr(mdf, "dtleTarget", np.full_like(dtle, np.nan)))
                lka_status = np.asarray(mdf.lkaInterventionStatus)
                steer_torque = np.asarray(mdf.steerWheelTorque)
                RateOfDeparture = np.asarray(mdf.rateOfDeparture)
                VehCurvature = np.asarray(mdf.vehCurvature)
                LaneCurvature = np.asarray(mdf.laneCurvature)
                use_case = np.asarray(getattr(mdf, "useCase", np.full_like(dtle, np.nan)))
            except AttributeError as e:
                warnings.warn(f"[Row {i}] Missing required signal: {e}")
                continue

            # --- Trim arrays to same length ---
            n = min(
                len(time),
                len(dtle),
                len(dtle_target),
                len(lka_status),
                len(steer_torque),
                len(RateOfDeparture),
                len(LaneCurvature),
                len(VehCurvature),
                len(use_case),
            )

            time, dtle, dtle_target, lka_status, steer_torque, RateOfDeparture, LaneCurvature, VehCurvature, use_case = (
                time[:n],
                dtle[:n],
                dtle_target[:n],
                lka_status[:n],
                steer_torque[:n],
                RateOfDeparture[:n],
                LaneCurvature[:n],
                VehCurvature[:n],
                use_case[:n],
            )



            # --- Detect intervention events ---
            try:
                start_indices, end_indices = detect_lka_events(time, lka_status)
            except Exception as e:
                warnings.warn(f"[Row {i}] detect_lka_events failed: {e}")
                continue

            if len(start_indices) == 0:
                warnings.warn(f"[Row {i}] No LKA events detected.")
                continue

            # --- Use first intervention (extendable later) ---
            start_idx = int(start_indices[0])
            end_idx = int(end_indices[0]) if len(end_indices) > 0 else len(time) - 1
            start_idx = max(0, min(start_idx, len(time) - 1))
            end_idx = max(0, min(end_idx, len(time) - 1))

            # --- Compute KPIs ---
            dtle_target_at_start = safe_scalar(dtle_target[start_idx])
            dtle_at_start = safe_scalar(dtle[start_idx])
            dtle_min_during = np.nanmin(dtle[start_idx:end_idx + 1])
            min_dtle_delta = safe_scalar(dtle_target_at_start - dtle_min_during)
            RoD_at_start = safe_scalar(RateOfDeparture[start_idx])
            Lane_Curv_at_start = safe_scalar(LaneCurvature[start_idx])
            Veh_Curv_at_start = safe_scalar(LaneCurvature[start_idx])
            use_case_at_start = safe_scalar(use_case[start_idx])


            is_high = np.any(np.abs(steer_torque[start_idx:end_idx + 1]) > self.driver_torque_th)

            # --- Save results ---
            self.kpi_table.loc[i, "MinDTLEDelta"] = min_dtle_delta
            self.kpi_table.loc[i, "TrigDTLE"] = dtle_at_start
            self.kpi_table.loc[i, "isWhlTrqHigh"] = bool(is_high)
            self.kpi_table.loc[i, "logTime"] = safe_scalar(time[start_idx])
            self.kpi_table.loc[i, "TrigRateOfDeparture"] = RoD_at_start
            self.kpi_table.loc[i, "TrigVehCurv"] = Veh_Curv_at_start
            self.kpi_table.loc[i, "TrigLaneCurv"] = Lane_Curv_at_start
            self.kpi_table.loc[i, "vehSpd"] = safe_scalar(
                getattr(mdf, "egoSpeedKph", [np.nan])[start_idx]
            )
            self.kpi_table.loc[i, "UseCase"] = use_case_at_start


            # --- Round & finalize ---
            self.kpi_table = self.kpi_table.round(4)

        print("\n✅ LKA KPI extraction completed successfully.")
