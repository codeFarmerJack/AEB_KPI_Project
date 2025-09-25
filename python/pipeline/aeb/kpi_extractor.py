import os
import warnings
import numpy as np
import pandas as pd
from scipy.io import loadmat
from utils import (
    create_kpi_table_from_json,
    accel_filter,
    find_aeb_intervention_start,
    find_aeb_intervention_end,
    interpolate_threshold_clamped,
)
# Your KPI metric functions should also live in utils or metrics
from utils.kpis import (
    kpi_distance,
    kpi_throttle,
    kpi_steering_wheel,
    kpi_lat_accel,
    kpi_yaw_rate,
    kpi_brake_mode,
    kpi_latency,
)


class KPIExtractor:
    """
    KPIExtractor class for processing AEB data and calculating KPIs
    """

    # --- Constant parameters (class-level defaults) ---
    PB_TGT_DECEL = -6.0       # m/s²
    FB_TGT_DECEL = -15.0      # m/s²
    TGT_TOL = 0.2             # tolerance for target decel
    AEB_END_THD = -4.9        # threshold for AEB end event
    TIME_IDX_OFFSET = 300     # offset for latAccel, yawRate, steering
    CUTOFF_FREQ = 10          # Hz cutoff frequency for filtering

    def __init__(self, config, event_detector):
        if config is None or event_detector is None:
            raise ValueError("Config and EventDetector are required.")

        if not hasattr(event_detector, "path_to_mat_chunks"):
            raise TypeError("event_detector must have path_to_mat_chunks attribute.")

        # Paths
        self.path_to_csv = event_detector.path_to_mat_chunks

        # File list
        self.file_list = [
            f for f in os.listdir(self.path_to_csv) if f.endswith(".mat")
        ]
        if not self.file_list:
            raise FileNotFoundError(f"No .mat files in {self.path_to_csv}")

        # KPI table
        self.kpi_table = create_kpi_table_from_json(
            config.kpiSchemaPath, len(self.file_list)
        )

        # Calibratables (cloned from config)
        self.calibratables = {
            "SteeringWheelAngle_Th": config.calibratables["SteeringWheelAngle_Th"],
            "AEB_SteeringAngleRate_Override": config.calibratables["AEB_SteeringAngleRate_Override"],
            "PedalPosProIncrease_Th": config.calibratables["PedalPosProIncrease_Th"].copy(),
            "YawrateSuspension_Th": config.calibratables["YawrateSuspension_Th"],
            "LateralAcceleration_th": config.calibratables["LateralAcceleration_th"],
        }
        # Scale pedal threshold (×100)
        self.calibratables["PedalPosProIncrease_Th"].iloc[1, :] *= 100

        self.signal_mat_chunk = None  # placeholder for active file

    # ------------------------------------------------------------------ #
    def process_all_mat_files(self):
        """Process all .mat files and calculate KPIs"""
        aeb_start_idx_list = []

        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_csv, fname)

            try:
                data = loadmat(fpath)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to load {fname}: {e}")
                continue

            # Expect a dict with 'signalMatChunk'
            if "signalMatChunk" in data:
                self.signal_mat_chunk = data["signalMatChunk"]
            else:
                # Sometimes MATLAB saves differently
                keys = [k for k in data.keys() if not k.startswith("__")]
                if len(keys) == 1:
                    self.signal_mat_chunk = data[keys[0]]
                    warnings.warn(f"⚠️ Using {keys[0]} as signalMatChunk in {fname}")
                else:
                    warnings.warn(f"⚠️ No signalMatChunk found in {fname}, skipping.")
                    continue

            # Convert MATLAB struct to dict of numpy arrays
            self.signal_mat_chunk = self._mat_struct_to_dict(self.signal_mat_chunk)

            # --- Preprocess ---
            self.signal_mat_chunk["egoSpeed"] = (
                self.signal_mat_chunk["egoSpeed"] * 3.6
            )  # m/s → km/h
            self.signal_mat_chunk["A2_Filt"] = accel_filter(
                self.signal_mat_chunk["time"],
                self.signal_mat_chunk["longActAccel"],
                self.CUTOFF_FREQ,
            )
            self.signal_mat_chunk["A1_Filt"] = accel_filter(
                self.signal_mat_chunk["time"],
                self.signal_mat_chunk["latActAccel"],
                self.CUTOFF_FREQ,
            )

            # Logging
            if "label" in self.kpi_table:
                self.kpi_table.at[i, "label"] = fname
            else:
                self.kpi_table.loc[i, "label"] = fname

            t0 = float(self.signal_mat_chunk["time"][0])
            self.kpi_table.loc[i, "logTime"] = round(t0, 2) if np.isfinite(t0) else np.nan

            # --- Locate intervention start M0 ---
            aeb_start_idx, M0 = find_aeb_intervention_start(self.signal_mat_chunk)
            aeb_start_idx_list.append(aeb_start_idx)

            self.kpi_table.loc[i, "m0IntvStart"] = (
                round(float(M0), 2) if np.isfinite(M0) else np.nan
            )
            veh_spd = self.signal_mat_chunk["egoSpeed"][aeb_start_idx]
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- Intervention end M2 ---
            is_veh_stopped, aeb_end_idx, M2 = find_aeb_intervention_end(
                self.signal_mat_chunk, aeb_start_idx
            )
            self.kpi_table.loc[i, "isVehStopped"] = is_veh_stopped
            self.kpi_table.loc[i, "m2IntvEnd"] = (
                round(float(M2), 2) if np.isfinite(M2) else np.nan
            )

            # Duration
            intv_dur = float(M2) - float(M0)
            self.kpi_table.loc[i, "intvDur"] = (
                round(intv_dur, 2) if np.isfinite(intv_dur) else np.nan
            )

            # --- Interpolate calibratables ---
            self.kpi_table.loc[i, "steerAngTh"] = interpolate_threshold_clamped(
                self.calibratables["SteeringWheelAngle_Th"], veh_spd
            )
            self.kpi_table.loc[i, "steerAngRateTh"] = interpolate_threshold_clamped(
                self.calibratables["AEB_SteeringAngleRate_Override"], veh_spd
            )
            self.kpi_table.loc[i, "pedalPosIncTh"] = interpolate_threshold_clamped(
                self.calibratables["PedalPosProIncrease_Th"], veh_spd
            )
            self.kpi_table.loc[i, "yawRateSuspTh"] = interpolate_threshold_clamped(
                self.calibratables["YawrateSuspension_Th"], veh_spd
            )
            self.kpi_table.loc[i, "latAccelTh"] = interpolate_threshold_clamped(
                self.calibratables["LateralAcceleration_th"], veh_spd
            )

            # --- KPI metrics ---
            kpi_distance(self, i, aeb_start_idx, aeb_end_idx)
            kpi_throttle(self, i, aeb_start_idx, self.kpi_table.loc[i, "pedalPosIncTh"])
            kpi_steering_wheel(
                self,
                i,
                aeb_start_idx,
                self.kpi_table.loc[i, "steerAngTh"],
                self.kpi_table.loc[i, "steerAngRateTh"],
            )
            kpi_lat_accel(self, i, aeb_start_idx, self.kpi_table.loc[i, "latAccelTh"])
            kpi_yaw_rate(self, i, aeb_start_idx, self.kpi_table.loc[i, "yawRateSuspTh"])
            kpi_brake_mode(self, i, aeb_start_idx)
            kpi_latency(self, i, aeb_start_idx)

    # ------------------------------------------------------------------ #
    def export_to_csv(self):
        """Export KPI table to CSV with headers including units"""
        output_filename = os.path.join(self.path_to_csv, "AEB_KPI_Results.csv")
        try:
            # Drop empty rows
            self.kpi_table = self.kpi_table.dropna(subset=["label"])
            self.kpi_table = self.kpi_table.sort_values("vehSpd")

            # Export
            self.kpi_table.to_csv(output_filename, index=False)
            print(f"✅ Exported KPI results to {output_filename}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export KPI results: {e}")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _mat_struct_to_dict(mat_struct):
        """
        Convert a MATLAB struct (from loadmat) into a Python dict of arrays.
        Assumes mat_struct is a numpy.void with dtype.names.
        """
        out = {}
        if hasattr(mat_struct, "dtype") and mat_struct.dtype.names:
            for field in mat_struct.dtype.names:
                try:
                    out[field] = np.atleast_1d(mat_struct[field][0, 0]).flatten()
                except Exception:
                    continue
        return out
