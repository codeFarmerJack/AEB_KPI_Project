import os
import warnings
import numpy as np
import pandas as pd
from asammdf import MDF

# --- Local utils imports ---
from utils.create_kpi_table import create_kpi_table_from_df
from utils.signal_filters import accel_filter
from utils.time_locators import (
    find_aeb_intv_start,
    find_aeb_intv_end,
)
from utils.process_calibratables import interpolate_threshold_clamped
from utils.kpis.aeb import (
    kpi_distance,
    kpi_throttle,
    kpi_steering_wheel,
    kpi_lat_accel,
    kpi_yaw_rate,
    kpi_brake_mode,
    kpi_latency,
)
from dataclasses import dataclass

@dataclass
class Thresholds:
    steer_ang_th: float 
    steer_ang_rate_th: float
    pedal_pos_inc_th: float
    yaw_rate_susp_th: float
    lat_accel_th: float

class KPIExtractor:
    """
    KPIExtractor for processing MDF (*.mf4) chunks and calculating KPIs
    """

    PB_TGT_DECEL    = -6.0      # unit: m/s^2
    FB_TGT_DECEL    = -15.0     # unit: m/s^2
    TGT_TOL         = 0.2       # unit: m/s^2
    AEB_END_THD     = -4.9      # unit: m/s^2
    TIME_IDX_OFFSET = 300       # time indices to advance to account for preconditions
    CUTOFF_FREQ     = 10        # cut off frequency used in butterworth filter

    def __init__(self, config, event_detector):
        if config is None or event_detector is None:
            raise ValueError("Config and EventDetector are required.")

        if not hasattr(event_detector, "path_to_mdf_chunks"):
            raise TypeError("event_detector must have path_to_mdf_chunks attribute.")

        self.path_to_chunks = event_detector.path_to_mdf_chunks
        self.file_list = [
            f for f in os.listdir(self.path_to_chunks) if f.endswith(".mf4")
        ]
        if not self.file_list:
            raise FileNotFoundError(f"No .mf4 files in {self.path_to_chunks}")

        # KPI table
        self.kpi_table = create_kpi_table_from_df(
            config.kpi_spec, len(self.file_list)
        )

        # --- Calibratables with safe mapping ---
        expected_keys = {
            "SteeringWheelAngle_Th": "SteeringWheelAngle_Th",
            "AEB_SteeringAngleRate_Override": "AEB_SteeringAngleRate_Override",
            "PedalPosProIncrease_Th": "PedalPosProIncrease_Th",
            "YawrateSuspension_Th": "YawrateSuspension_Th",
            "LateralAcceleration_th": "LateralAcceleration_th",
        }

        self.calibratables = {}
        for internal_name, cfg_key in expected_keys.items():
            if cfg_key in config.calibratables:
                self.calibratables[internal_name] = config.calibratables[cfg_key]
            else:
                warnings.warn(
                    f"⚠️ Missing calibratable '{cfg_key}' in config. Using empty DataFrame."
                )
                self.calibratables[internal_name] = pd.DataFrame()

        # Scale pedal threshold (×100) if possible
        if "PedalPosProIncrease_Th" in self.calibratables:
            val = self.calibratables["PedalPosProIncrease_Th"]
            if isinstance(val, dict) and "y" in val:
                val["y"] = [yy * 100 for yy in val["y"] if yy is not None]
            else:
                warnings.warn("⚠️ PedalPosProIncrease_Th is not in expected dict format.")

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all .mf4 files and calculate KPIs"""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_chunks, fname)
            print(f"🔍 Processing {fname}")

            # --- Save file name into KPI table for traceability ---
            if "label" in self.kpi_table.columns:
                self.kpi_table.loc[i, "label"] = fname
            else:
                # fallback if schema doesn't define "label"
                self.kpi_table.insert(0, "label", "")
                self.kpi_table.loc[i, "label"] = fname

            try:
                mdf = MDF(fpath)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to read {fname}: {e}")
                continue

            # --- Robust handling of time channel ---
            try:
                # Try group 0 by default
                time = mdf.get("time", group=0).samples
            except Exception as e:
                warnings.warn(f"⚠️ Could not fetch 'time' channel directly: {e}")
                # fallback: use master time of first group
                try:
                    time = mdf.get_channel_group(0).get_master().samples
                except Exception:
                    # last resort: synthesize a time vector
                    n = len(mdf.get(list(mdf.channels_db.keys())[0]).samples)
                    time = np.arange(n, dtype=float)
                    warnings.warn("⚠️ Synthesized time vector (equidistant).")

                signal_chunk = {}
                for sig_name in [
                    "time",
                    "egoSpeed",
                    "longActAccel",
                    "latActAccel",
                    "throttleValue",
                    "brakePedalPressed",
                    "yawRate",
                    "steerWheelAngle",
                    "steerWheelAngleSpeed",
                    "aebTargetDecel",
                ]:
                    try:
                        signal_chunk[sig_name] = mdf.get(sig_name).samples.flatten()
                    except Exception:
                        warnings.warn(f"⚠️ Missing signal {sig_name} in {fname}")
                        signal_chunk[sig_name] = np.full_like(time, np.nan, dtype=float)

                signal_chunk["time"] = time

                # --- Preprocess ---
                signal_chunk["egoSpeed"] *= 3.6         # m/s → km/h
                signal_chunk["longActAccelFlt"] = accel_filter(
                    signal_chunk["time"], signal_chunk["longActAccel"], self.CUTOFF_FREQ
                )
                signal_chunk["latActAccelFlt"] = accel_filter(
                    signal_chunk["time"], signal_chunk["latActAccel"], self.CUTOFF_FREQ
                )

                t0 = float(signal_chunk["time"][0])
                if "logTime" in self.kpi_table.columns:
                    self.kpi_table.loc[i, "logTime"] = round(t0, 2) if np.isfinite(t0) else np.nan

                # --- KPI calculations ---
                aeb_start_idx, M0 = find_aeb_intv_start(signal_chunk, self.PB_TGT_DECEL)
                is_veh_stopped, aeb_end_idx, M2 = find_aeb_intv_end(
                    signal_chunk, aeb_start_idx, self.AEB_END_THD
                )

                self.kpi_table.loc[i, "aebIntvStartTime"] = round(float(M0), 2) if np.isfinite(M0) else np.nan
                self.kpi_table.loc[i, "isVehStopped"] = is_veh_stopped
                self.kpi_table.loc[i, "aebIntvEndTime"] = round(float(M2), 2) if np.isfinite(M2) else np.nan
                if np.isfinite(M0) and np.isfinite(M2):
                    self.kpi_table.loc[i, "intvDur"] = round(float(M2) - float(M0), 2)

                veh_spd = signal_chunk["egoSpeed"][aeb_start_idx]
                self.kpi_table.loc[i, "vehSpd"] = veh_spd

                # --- Interpolated calibratables bundled into Thresholds dataclass ---
                thd = Thresholds(
                    steer_ang_th = interpolate_threshold_clamped(
                        self.calibratables["SteeringWheelAngle_Th"], veh_spd
                    ),
                    steer_ang_rate_th = interpolate_threshold_clamped(
                        self.calibratables["AEB_SteeringAngleRate_Override"], veh_spd
                    ),
                    pedal_pos_inc_th = interpolate_threshold_clamped(
                        self.calibratables["PedalPosProIncrease_Th"], veh_spd
                    ),
                    yaw_rate_susp_th = interpolate_threshold_clamped(
                        self.calibratables["YawrateSuspension_Th"], veh_spd
                    ),
                    lat_accel_th = interpolate_threshold_clamped(
                        self.calibratables["LateralAcceleration_th"], veh_spd
                    ),
                )

                # Save into KPI table
                self.kpi_table.loc[i, "steerAngTh"]       = thd.steer_ang_th
                self.kpi_table.loc[i, "steerAngRateTh"]  = thd.steer_ang_rate_th
                self.kpi_table.loc[i, "pedalPosIncTh"]   = thd.pedal_pos_inc_th
                self.kpi_table.loc[i, "yawRateSuspTh"]   = thd.yaw_rate_susp_th
                self.kpi_table.loc[i, "latAccelTh"]       = thd.lat_accel_th


                # KPI metrics
                kpi_distance(self, i, aeb_start_idx, aeb_end_idx)
                kpi_throttle(self, i, aeb_start_idx, thd.pedal_pos_inc_th)
                kpi_steering_wheel(self, i, aeb_start_idx, thd.steer_ang_th, thd.steer_ang_rate_th)
                kpi_lat_accel(self, i, aeb_start_idx, thd.lat_accel_th)
                kpi_yaw_rate(self, i, aeb_start_idx, thd.yaw_rate_susp_th)
                kpi_brake_mode(self, i, aeb_start_idx)
                kpi_latency(self, i, aeb_start_idx)

    # ------------------------------------------------------------------ #
    def export_to_csv(self):
        """Export KPI table to CSV with units in the header"""
        output_filename = os.path.join(self.path_to_chunks, "AEB_KPI_Results.csv")
        try:
            df = self.kpi_table.copy()

            # Drop rows without label (only if label exists)
            if "label" in df.columns:
                df = df.dropna(subset=["label"])

            # Sort by speed if available
            if "vehSpd" in df.columns:
                df = df.sort_values("vehSpd")

            # Build header with display names (fall back to colname if missing)
            display_map = df.attrs.get("display_names", {})
            renamed = {col: display_map.get(col, col) for col in df.columns}

            # Always force "label" to stay plain
            renamed["label"] = "label"

            # Rename for export
            df = df.rename(columns=renamed)

            # Export
            df.to_csv(output_filename, index=False, encoding="utf-8-sig")
            print(f"✅ Exported KPI results to {output_filename}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export KPI results: {e}")

