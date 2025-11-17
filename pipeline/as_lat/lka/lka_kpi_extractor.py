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
    def __init__(self, config, event_segmenter=None):
        super().__init__(config, event_segmenter, "in_path_lka_chunks", feature_name="LKA")
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
                time            = self._prepare_time(mdf)
                dtle            = np.asarray(mdf.dtle)
                dtle_target     = np.asarray(getattr(mdf, "dtleTarget", np.full_like(dtle, np.nan)))
                lka_status      = np.asarray(mdf.lkaInterventionStatus)
                steer_torque    = np.asarray(mdf.steerWheelTorque)
                RateOfDeparture = np.asarray(mdf.rateOfDeparture)
                VehCurvature    = np.asarray(mdf.vehCurvature)
                LaneCurvature   = np.asarray(mdf.laneCurvature)
                use_case        = np.asarray(getattr(mdf, "useCase", np.full_like(dtle, np.nan)))
            except AttributeError as e:
                warnings.warn(f"[Row {i}] Missing required signal: {e}")
                continue
           
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
            dtle_at_start        = safe_scalar(dtle[start_idx])
            dtle_min_during      = np.nanmin(dtle[start_idx:end_idx + 1])
            min_dtle_delta       = safe_scalar(dtle_target_at_start - dtle_min_during)
            RoD_at_start         = safe_scalar(RateOfDeparture[start_idx])
            Lane_Curv_at_start   = safe_scalar(LaneCurvature[start_idx])
            Veh_Curv_at_start    = safe_scalar(VehCurvature[start_idx])
            use_case_at_start    = safe_scalar(use_case[start_idx])


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

    def process_lka_availability(self, folder_feature_logs):
        """
        Compute feature availability across whole logs:
        - % of distance LKA is available on left
        - % of distance LKA is available on right

        Results go ONLY into:
            self.overall_kpi_table (Excel-defined table)
        """

        print("\n📊 Processing LKA Feature Availability KPIs...")

        # ============================================================
        # Pre-compute: Determine NON-COMMON feature(s) from schema
        # Example: {"label": "Common", "AvailDistPctLeft": "LKA", "AvailDistPctRight": "LKA"}
        # ============================================================
        if hasattr(self, "overall_kpi_feature_map") and self.overall_kpi_feature_map:
            non_common_features = {
                f for f in self.overall_kpi_feature_map.values()
                if f and str(f).upper() != "COMMON"
            }
            # Usually a single feature like "LKA"
            merged_feature_name = next(iter(non_common_features), self.FEATURE_NAME)
        else:
            merged_feature_name = self.FEATURE_NAME

        # ============================================================
        # Process every extracted MF4 file (one output row per file)
        # ============================================================
        for i, fname in enumerate(self.file_list_extracted):

            fpath = os.path.join(folder_feature_logs, fname)
            print(f"\n🚗 [{i+1}/{len(self.file_list_extracted)}]   Feature availability from: {fname}")

            mdf = self._load_mdf(fpath)
            if mdf is None:
                warnings.warn(f"Missing extracted MF4 for {fname}")
                continue

            try:
                time        = self._prepare_time(mdf)
                ready_left  = np.asarray(mdf.lkaReadyLeft)
                ready_right = np.asarray(mdf.lkaReadyRight)
                lka_block   = np.asarray(mdf.lkaPrecondBlk)
                lka_abort   = np.asarray(mdf.lkaAbort)
                speed_mps   = np.asarray(mdf.egoSpeed)
            except AttributeError as e:
                warnings.warn(f"[Feature Availability Row {i}] Missing required signal: {e}")
                continue

            # --- dt ---
            dt = np.diff(time, prepend=time[0])
            dt = np.maximum(dt, 0.0)

            # --- distance ---
            dist = speed_mps * dt
            total_dist = np.sum(dist)

            if total_dist <= 0:
                warnings.warn(f"[Row {i}] Total distance = 0 → skipping availability KPI.")
                continue

            # --- Availability conditions ---
            global_ok   = (lka_block == 0) & (lka_abort == 0)
            avail_left  = (ready_left == 1) & global_ok
            avail_right = (ready_right == 1) & global_ok

            pct_left  = np.sum(dist[avail_left])  / total_dist * 100
            pct_right = np.sum(dist[avail_right]) / total_dist * 100

            # ============================================================
            # SAVE into one row of overall_kpi_table
            # ============================================================
            if self.overall_kpi_table is not None:

                row_idx = i  # one row per file

                # --- label (Common KPI)
                if "label" in self.overall_kpi_table.columns:
                    self.overall_kpi_table.loc[row_idx, "label"] = fname

                # --- feature (merged feature from schema)
                if "feature" in self.overall_kpi_table.columns:
                    self.overall_kpi_table.loc[row_idx, "feature"] = merged_feature_name

                # --- KPI values (only write columns that exist in the table)
                if "AvailDistPctLeft" in self.overall_kpi_table.columns:
                    self.overall_kpi_table.loc[row_idx, "AvailDistPctLeft"] = f"{pct_left:.2f}"

                if "AvailDistPctRight" in self.overall_kpi_table.columns:
                    self.overall_kpi_table.loc[row_idx, "AvailDistPctRight"] = f"{pct_right:.2f}"

        print("\n✅ Feature availability KPIs completed successfully.\n")




