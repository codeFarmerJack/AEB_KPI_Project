import os
import warnings
import numpy as np
import pandas as pd

# --- Local utils imports ---
from utils.signal_mdf import SignalMDF
from utils.create_kpi_table import create_kpi_table_from_df
from utils.time_locators import find_aeb_intv_start, find_aeb_intv_end
from utils.process_calibratables import interpolate_threshold_clamped

# ✅ Import all KPI functions directly via __init__.py
from utils.kpis.aeb import (
    brake_mode,
    distance,
    lat_accel,
    latency,
    steering_wheel,
    throttle,
    yaw_rate,
)

from dataclasses import dataclass


# ------------------------------------------------------------------ #
# Utility: safe conversion to scalar
# ------------------------------------------------------------------ #
def safe_scalar(x):
    """Convert array-like or weird types to scalar float or NaN."""
    if x is None:
        return np.nan
    if isinstance(x, (list, np.ndarray, pd.Series)):
        if len(x) == 0:
            return np.nan
        return float(np.ravel(x)[0])
    try:
        return float(x)
    except Exception:
        return np.nan


# ------------------------------------------------------------------ #
# Threshold container
# ------------------------------------------------------------------ #
@dataclass
class Thresholds:
    steer_ang_th: float
    steer_ang_rate_th: float
    pedal_pos_inc_th: float
    yaw_rate_susp_th: float
    lat_accel_th: float


# ------------------------------------------------------------------ #
# AEB KPI Extractor
# ------------------------------------------------------------------ #
class KpiExtractor:
    """Extracts AEB KPI metrics from MF4 chunks."""

    # --- Fallback defaults (used if not overridden by config) ---
    PB_TGT_DECEL    = -6.0      # m/s²
    FB_TGT_DECEL    = -15.0     # m/s²
    TGT_TOL         = 0.2       # m/s²
    AEB_END_THD     = -4.9      # m/s²
    TIME_IDX_OFFSET = 300       # samples (~3s at 0.01s rate) 

    def __init__(self, config, event_detector):
        if config is None or event_detector is None:
            raise ValueError("Config and EventDetector are required.")
        if not hasattr(event_detector, "path_to_mdf_chunks"):
            raise TypeError("event_detector must have path_to_mdf_chunks attribute.")

        # --- Setup paths ---
        self.path_to_mdf     = event_detector.path_to_mdf
        self.path_to_results = os.path.join(self.path_to_mdf, "analysis_results")
        
        if not os.path.exists(self.path_to_results):
            os.makedirs(self.path_to_results)
       
        self.path_to_chunks  = event_detector.path_to_mdf_chunks
        self.file_list       = [f for f in os.listdir(self.path_to_chunks) if f.endswith(".mf4")]

        if not self.file_list:
            raise FileNotFoundError(f"No .mf4 files in {self.path_to_chunks}")

        # --- KPI table creation ---
        self.kpi_table = create_kpi_table_from_df(config.kpi_spec, feature="AEB")

        # --- Load calibratables safely ---
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
                warnings.warn(f"⚠️ Missing calibratable '{cfg_key}' in config.")
                self.calibratables[internal_name] = pd.DataFrame()

        # --- Initialize parameters ---
        self._apply_defaults()

        # --- Apply parameter overrides from Config.params (if present) ---
        if hasattr(config, "params") and isinstance(config.params, dict):
            params = config.params
            print("⚙️ Applying parameter overrides from config.params")

            self.pb_tgt_decel    = float(params.get("PB_TGT_DECEL", self.pb_tgt_decel))
            self.fb_tgt_decel    = float(params.get("FB_TGT_DECEL", self.fb_tgt_decel))
            self.tgt_tol         = float(params.get("TGT_TOL", self.tgt_tol))
            self.aeb_end_thd     = float(params.get("AEB_END_THD", self.aeb_end_thd))
            self.time_idx_offset = int(params.get("TIME_IDX_OFFSET", self.time_idx_offset))

        # --- Debug summary ---
        print(
            f"\n📊 KPI Parameter Summary:\n"
            f"   PB_TGT_DECEL    = {self.pb_tgt_decel}\n"
            f"   FB_TGT_DECEL    = {self.fb_tgt_decel}\n"
            f"   TGT_TOL         = {self.tgt_tol}\n"
            f"   AEB_END_THD     = {self.aeb_end_thd}\n"
            f"   TIME_IDX_OFFSET = {self.time_idx_offset}\n"
        )

    # ------------------------------------------------------------------ #
    def _apply_defaults(self):
        """Fallback defaults if Config.params does not override them."""
        self.pb_tgt_decel    = self.PB_TGT_DECEL
        self.fb_tgt_decel    = self.FB_TGT_DECEL
        self.tgt_tol         = self.TGT_TOL
        self.aeb_end_thd     = self.AEB_END_THD
        self.time_idx_offset = self.TIME_IDX_OFFSET

        print(
            f"⚙️ Using default parameters: "
            f"PB_TGT_DECEL={self.pb_tgt_decel}, FB_TGT_DECEL={self.fb_tgt_decel}, "
            f"TGT_TOL={self.tgt_tol}, AEB_END_THD={self.aeb_end_thd}"
        )

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all .mf4 chunk files and calculate KPIs."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_chunks, fname)
            print(f"🔍 Processing {fname}")

            if "label" not in self.kpi_table.columns:
                self.kpi_table.insert(0, "label", "")
            self.kpi_table.loc[i, "label"] = fname

            try:
                mdf = SignalMDF(fpath)
            except Exception as e:
                warnings.warn(f"⚠️ Failed to read {fname}: {e}")
                continue

            # --- Time vector ---
            time = mdf.time
            if time is None or len(time) == 0:
                try:
                    time = mdf.get_master(0).flatten()
                except Exception:
                    n = len(mdf.groups[0].channels[0].samples) if mdf.groups else 0
                    time = np.arange(n, dtype=float)
                warnings.warn("⚠️ Synthesized time vector (equidistant).")

            # --- Signals ---
            ego_speed     = mdf.egoSpeedKph   
            aeb_tgt_decel = mdf.aebTargetDecel

            # --- KPI event detection ---
            aeb_start_idx, aeb_start_time = find_aeb_intv_start(
                {"aebTargetDecel": aeb_tgt_decel, "time": time}, self.pb_tgt_decel
            )
            is_veh_stopped, aeb_end_idx, aeb_end_time = find_aeb_intv_end(
                {"egoSpeed": ego_speed, "aebTargetDecel": aeb_tgt_decel, "time": time},
                aeb_start_idx,
                self.aeb_end_thd,
            )

            # --- Save intervention info ---
            self.kpi_table.loc[i, "logTime"]          = safe_scalar(aeb_start_time)
            self.kpi_table.loc[i, "aebIntvStartTime"] = safe_scalar(aeb_start_time)
            self.kpi_table.loc[i, "isVehStopped"]     = bool(is_veh_stopped)
            self.kpi_table.loc[i, "aebIntvEndTime"]   = safe_scalar(aeb_end_time)

            if np.isfinite(safe_scalar(aeb_start_time)) and np.isfinite(safe_scalar(aeb_end_time)):
                self.kpi_table.loc[i, "intvDur"] = round(
                    float(aeb_end_time) - float(aeb_start_time), 2
                )

            # --- Vehicle speed at start ---
            veh_spd = np.nan
            if aeb_start_idx is not None and aeb_start_idx < len(ego_speed):
                veh_spd = safe_scalar(ego_speed[aeb_start_idx])
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- Thresholds ---
            thd = Thresholds(
                steer_ang_th      = interpolate_threshold_clamped(self.calibratables["SteeringWheelAngle_Th"], veh_spd),
                steer_ang_rate_th = interpolate_threshold_clamped(self.calibratables["AEB_SteeringAngleRate_Override"], veh_spd),
                pedal_pos_inc_th  = interpolate_threshold_clamped(self.calibratables["PedalPosProIncrease_Th"], veh_spd),
                yaw_rate_susp_th  = interpolate_threshold_clamped(self.calibratables["YawrateSuspension_Th"], veh_spd),
                lat_accel_th      = interpolate_threshold_clamped(self.calibratables["LateralAcceleration_th"], veh_spd),
            )

            # --- Save thresholds ---
            self.kpi_table.loc[i, "steerAngTh"]     = safe_scalar(thd.steer_ang_th)
            self.kpi_table.loc[i, "steerAngRateTh"] = safe_scalar(thd.steer_ang_rate_th)
            self.kpi_table.loc[i, "pedalPosIncTh"]  = safe_scalar(thd.pedal_pos_inc_th)
            self.kpi_table.loc[i, "yawRateSuspTh"]  = safe_scalar(thd.yaw_rate_susp_th)
            self.kpi_table.loc[i, "latAccelTh"]     = safe_scalar(thd.lat_accel_th)

            # --- KPI metrics ---
            distance(mdf, self.kpi_table, i, aeb_start_idx, aeb_end_idx)
            throttle(mdf, self.kpi_table, i, aeb_start_idx, thd.pedal_pos_inc_th)
            steering_wheel(mdf, self.kpi_table, i, aeb_start_idx, thd.steer_ang_th, thd.steer_ang_rate_th, self.time_idx_offset)
            lat_accel(mdf, self.kpi_table, i, aeb_start_idx, thd.lat_accel_th, self.time_idx_offset)
            yaw_rate(mdf, self.kpi_table, i, aeb_start_idx, thd.yaw_rate_susp_th, self.time_idx_offset)
            brake_mode(mdf, self.kpi_table, i, aeb_start_idx, self.pb_tgt_decel, self.fb_tgt_decel, self.tgt_tol)
            latency(mdf, self.kpi_table, i, aeb_start_idx)

            self.kpi_table = self.kpi_table.round(2)

    # ------------------------------------------------------------------ #
    def export_to_excel(self):
        """Export KPI results to Excel (sheet: 'aeb')."""
        output_filename = os.path.join(self.path_to_results, "AS-Long_KPI_Results.xlsx")

        try:
            df = self.kpi_table.copy()
            if "label" in df.columns:
                df = df.dropna(subset=["label"])
            if "vehSpd" in df.columns:
                df = df.sort_values("vehSpd")

            display_map = df.attrs.get("display_names", {})
            renamed = {col: display_map.get(col, col) for col in df.columns}
            renamed["label"] = "label"
            df = df.rename(columns=renamed)

            with pd.ExcelWriter(output_filename, engine="openpyxl", mode="w") as writer:
                df.to_excel(writer, sheet_name="aeb", index=False)

            print(f"✅ Exported KPI results to Excel → {output_filename} (sheet: 'aeb')")
        except Exception as e:
            warnings.warn(f"⚠️ Failed to export KPI results: {e}")