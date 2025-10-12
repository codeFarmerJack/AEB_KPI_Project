import os
import warnings
import numpy as np
import pandas as pd

# --- Local utils imports ---
from utils.signal_mdf import SignalMDF
from utils.create_kpi_table import create_kpi_table_from_df
from utils.data_utils import safe_scalar

# Import all FCW KPI functions (via __init__.py)
from utils.kpis.fcw import *


# ------------------------------------------------------------------ #
# FCW KPI Extractor
# ------------------------------------------------------------------ #
class FcwKpiExtractor:
    """Extracts FCW KPI metrics from MF4 chunks."""

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
        self.kpi_table = create_kpi_table_from_df(config.kpi_spec, feature="FCW")

        # --- Initialize parameters ---
        self._apply_defaults()

        # --- Apply overrides from Config.params (if present) ---
        if hasattr(config, "params") and isinstance(config.params, dict):
            params = config.params
            print("⚙️ Applying parameter overrides from config.params")

            self.pb_tgt_decel    = float(params.get("PB_TGT_DECEL", self.pb_tgt_decel))
            self.fb_tgt_decel    = float(params.get("FB_TGT_DECEL", self.fb_tgt_decel))
            self.tgt_tol         = float(params.get("TGT_TOL", self.tgt_tol))
            self.fcw_end_thd     = float(params.get("FCW_END_THD", self.fcw_end_thd))
            self.time_idx_offset = int(params.get("TIME_IDX_OFFSET", self.time_idx_offset))

        # --- Debug summary ---
        print(
            f"\n📊 FCW KPI Parameter Summary:\n"
            f"   PB_TGT_DECEL    = {self.pb_tgt_decel}\n"
            f"   FB_TGT_DECEL    = {self.fb_tgt_decel}\n"
            f"   TGT_TOL         = {self.tgt_tol}\n"
            f"   FCW_END_THD     = {self.fcw_end_thd}\n"
            f"   TIME_IDX_OFFSET = {self.time_idx_offset}\n"
        )

    # ------------------------------------------------------------------ #
    def _apply_defaults(self):
        """Fallback defaults if Config.params does not override them."""
        self.pb_tgt_decel    = self.PB_TGT_DECEL
        self.fb_tgt_decel    = self.FB_TGT_DECEL
        self.tgt_tol         = self.TGT_TOL
        self.fcw_end_thd     = self.FCW_END_THD
        self.time_idx_offset = self.TIME_IDX_OFFSET

        print(
            f"⚙️ Using default parameters: "
            f"PB_TGT_DECEL={self.pb_tgt_decel}, FB_TGT_DECEL={self.fb_tgt_decel}, "
            f"TGT_TOL={self.tgt_tol}, FCW_END_THD={self.fcw_end_thd}"
        )

    # ------------------------------------------------------------------ #
    def process_all_mdf_files(self):
        """Process all .mf4 chunk files and calculate KPIs."""
        for i, fname in enumerate(self.file_list):
            fpath = os.path.join(self.path_to_chunks, fname)
            print(f"🔍 Processing {fname}")

            # --- Prepare label column ---
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

            # --- Extract key signals ---
            ego_speed     = mdf.egoSpeedKph
            fcw_request   = mdf.fcwRequest
            accel         = getattr(mdf, "vehAccel", None)

            # --- FCW event detection ---
            fcw_start_idx, fcw_start_time = find_aeb_intv_start(
                {"aebTargetDecel": fcw_request, "time": time}, self.pb_tgt_decel
            )
            is_veh_stopped, fcw_end_idx, fcw_end_time = find_aeb_intv_end(
                {"egoSpeed": ego_speed, "aebTargetDecel": fcw_request, "time": time},
                fcw_start_idx,
                self.fcw_end_thd,
            )

            # --- Save core timings ---
            self.kpi_table.loc[i, "logTime"]         = safe_scalar(fcw_start_time)
            self.kpi_table.loc[i, "fcwStartTime"]    = safe_scalar(fcw_start_time)
            self.kpi_table.loc[i, "isVehStopped"]    = bool(is_veh_stopped)
            self.kpi_table.loc[i, "fcwEndTime"]      = safe_scalar(fcw_end_time)

            if np.isfinite(safe_scalar(fcw_start_time)) and np.isfinite(safe_scalar(fcw_end_time)):
                self.kpi_table.loc[i, "fcwDur"] = round(
                    float(fcw_end_time) - float(fcw_start_time), 2
                )

            # --- Vehicle speed at start ---
            veh_spd = np.nan
            if fcw_start_idx is not None and fcw_start_idx < len(ego_speed):
                veh_spd = safe_scalar(ego_speed[fcw_start_idx])
            self.kpi_table.loc[i, "vehSpd"] = veh_spd

            # --- KPI metric calculations ---
            # (Each subfunction updates kpi_table in place)
            brake_jerk(mdf, self.kpi_table, i, fcw_start_idx)
            # Add other FCW KPIs here (placeholders)
            # e.g. peakDecel(), peakJerk(), fcw_latency()

            # Round final KPI table for export
            self.kpi_table = self.kpi_table.round(2)

    # ------------------------------------------------------------------ #
    def export_to_excel(self):
        """Export FCW KPI results to Excel (sheet: 'fcw')."""
        output_filename = os.path.join(self.path_to_results, "AS-Long_KPI_Results.xlsx")

        try:
            df = self.kpi_table.copy()

            # --- Clean & sort ---
            if "label" in df.columns:
                df = df.dropna(subset=["label"])
            if "vehSpd" in df.columns:
                df = df.sort_values("vehSpd")

            # --- Apply display names (from schema) ---
            display_map = df.attrs.get("display_names", {})
            renamed = {col: display_map.get(col, col) for col in df.columns}
            renamed["label"] = "label"
            df = df.rename(columns=renamed)

            # --- Determine write mode ---
            file_exists = os.path.exists(output_filename)

            if file_exists:
                # ✅ File exists — append/replace only 'fcw' sheet
                with pd.ExcelWriter(
                    output_filename,
                    engine="openpyxl",
                    mode="a",
                    if_sheet_exists="replace",
                ) as writer:
                    df.to_excel(writer, sheet_name="fcw", index=False)
                print(f"🔁 Updated sheet 'fcw' in existing workbook → {output_filename}")

            else:
                # 🆕 File does not exist — create new workbook
                with pd.ExcelWriter(output_filename, engine="openpyxl", mode="w") as writer:
                    df.to_excel(writer, sheet_name="fcw", index=False)
                print(f"🆕 Created new workbook and exported FCW KPIs → {output_filename}")

        except Exception as e:
            warnings.warn(f"⚠️ Failed to export FCW KPI results: {e}")

