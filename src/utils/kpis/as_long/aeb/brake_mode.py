import numpy as np
import pandas as pd
import warnings
from src.utils.signal_mdf import get_signal

class AebBrakeModeCalculator:
    """
    Determines Partial Braking (PB) and Full Braking (FB)
    activation and durations for AEB events.
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize from parent AebEventKpiExtractor instance.
        """
        self.pb_tgt_decel = extractor.pb_tgt_decel
        self.fb_tgt_decel = extractor.fb_tgt_decel
        self.tgt_tol      = extractor.tgt_tol

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_brake_mode(self, mdf, kpi_table, row_idx, aeb_start_idx):
        """
        Detect PB/FB activation and compute their durations.
        PB duration is measured only for the first PB period that occurs
        before transitioning to full braking (FB).
        Updates kpi_table in place.
        """
        target_decel = get_signal(mdf, "aebTargetDecel")
        time         = get_signal(mdf, "time")
        if target_decel is None or time is None:
            warnings.warn(f"[Row {row_idx}] Missing required signals 'aebTargetDecel' or 'time'")
            return

        if aeb_start_idx is None or aeb_start_idx >= len(time):
            warnings.warn(f"[Row {row_idx}] Invalid AEB start index")
            return

        aeb_end_req = len(time) - 1

        # Ensure required columns exist
        for col, default, dtype in [
            ("pbDur", np.nan, "float"),
            ("fbDur", np.nan, "float"),
            ("isPBOn", False, "bool"),
            ("isFBOn", False, "bool"),
        ]:
            if col not in kpi_table.columns:
                kpi_table[col] = pd.Series([default] * len(kpi_table), dtype=dtype)

        # --- Step 1: Segment from AEB start to end
        segment = target_decel[aeb_start_idx:aeb_end_req + 1]

        # --- Step 2: Find PB / FB candidate indices
        pb_idx = np.where(np.abs(segment - self.pb_tgt_decel) <= self.tgt_tol)[0]
        fb_idx = np.where(np.abs(segment - self.fb_tgt_decel) <= self.tgt_tol)[0]

        is_pb_on = len(pb_idx) > 0
        is_fb_on = len(fb_idx) > 0

        pb_dur_val = 0.0
        fb_dur_val = 0.0

        # --- Step 3: Compute PB duration (only before first FB)
        if is_pb_on:
            if is_fb_on:
                first_fb_idx = aeb_start_idx + fb_idx[0]
                # keep only PB samples that occur before first FB
                pb_idx = pb_idx[pb_idx + aeb_start_idx < first_fb_idx]
                if len(pb_idx) == 0:
                    is_pb_on = False
                else:
                    pb_start    = aeb_start_idx + pb_idx[0]
                    pb_end      = aeb_start_idx + pb_idx[-1]
                    pb_dur_val  = time[pb_end] - time[pb_start]
            else:
                pb_start    = aeb_start_idx + pb_idx[0]
                pb_end      = aeb_start_idx + pb_idx[-1]
                pb_dur_val  = time[pb_end] - time[pb_start]

        # --- Step 4: Compute FB duration
        if is_fb_on:
            fb_start    = aeb_start_idx + fb_idx[0]
            fb_end      = aeb_start_idx + fb_idx[-1]
            fb_dur      = time[fb_end] - time[fb_start]
            fb_dur_val  = round(float(fb_dur), 3) if np.isfinite(fb_dur) else 0.0
        else:
            fb_dur_val = 0.0

        # --- Step 5: Write to KPI table
        kpi_table.at[row_idx, "pbDur"]  = round(float(pb_dur_val), 3) if np.isfinite(pb_dur_val) else 0.0
        kpi_table.at[row_idx, "fbDur"]  = fb_dur_val
        kpi_table.at[row_idx, "isPBOn"] = is_pb_on
        kpi_table.at[row_idx, "isFBOn"] = is_fb_on

        # --- Step 6: Debug print
        #print(
        #    f"🧩 [Row {row_idx}] Brake Mode Detection:\n"
        #    f"   • PB: {'ON' if is_pb_on else 'OFF'} | Duration = {kpi_table.at[row_idx, 'pbDur']:.3f} s (before FB)\n"
        #    f"   • FB: {'ON' if is_fb_on else 'OFF'} | Duration = {kpi_table.at[row_idx, 'fbDur']:.3f} s\n"
        #)
