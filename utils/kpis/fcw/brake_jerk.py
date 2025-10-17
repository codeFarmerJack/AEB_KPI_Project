import numpy as np
import warnings
from utils.data_utils import safe_scalar
from utils.event_detector.decel import detect_decel_onset, detect_brake_jerk_end


class FcwBrakeJerkCalculator:
    """
    Detects brake jerk start/end based on derivative of acceleration signal
    during FCW (Forward Collision Warning) events.
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize using parameters from the parent FcwKpiExtractor instance.
        """
        self.brakejerk_jerk_neg_thd = extractor.brakejerk_jerk_neg_thd
        self.brakejerk_jerk_pos_thd = extractor.brakejerk_jerk_pos_thd
        self.brakejerk_min_speed    = extractor.brakejerk_min_speed
        self.brakejerk_max_speed    = extractor.brakejerk_max_speed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_brake_jerk(self, mdf, kpi_table, row_idx: int):
        """
        Detect brake jerk start/end using derivative of acceleration signal (no smoothing).

        Parameters
        ----------
        mdf : SignalMDF
            MF4 chunk with signals (time, longActAccelFlt, fcwRequest, egoSpeedKph)
        kpi_table : pd.DataFrame
            The KPI table to update in place.
        row_idx : int
            Row index in the KPI table.
        """

        neg_thd = self.brakejerk_jerk_neg_thd
        pos_thd = self.brakejerk_jerk_pos_thd
        min_spd = self.brakejerk_min_speed
        max_spd = self.brakejerk_max_speed

        # --- Ensure KPI columns exist ---
        cols = ["brakeJerkDur", "brakeJerkStart", "brakeJerkEnd",
                "brakeJerkMax", "brakeAccelMin"]
        for c in cols:
            if c not in kpi_table.columns:
                kpi_table[c] = np.nan

        def _fill_zero(reason: str):
            """Fill zeros directly into the table."""
            for c in cols:
                kpi_table.at[row_idx, c] = 0.0
            print(f"   ⚠️ [Row {row_idx}] No valid brake jerk detected ({reason}) → filled 0s.")
            return

        # --- Extract signals safely ---
        try:
            time  = np.asarray(mdf.time)
            accel = np.asarray(mdf.longActAccelFlt)
            fcw   = np.asarray(mdf.fcwRequest)
            spd   = np.asarray(mdf.egoSpeedKph)
        except AttributeError:
            _fill_zero("missing required signals")
            return

        # --- Detect FCW rising edge ---
        edges = np.where((fcw[:-1] < 3) & (fcw[1:] >= 3))[0]
        if len(edges) == 0:
            _fill_zero("no FCW trigger")
            return

        t0 = time[edges[0] + 1]

        # --- Define analysis window ---
        mask = (time >= t0 - 0.2) & (time <= t0 + 1.0)
        if not np.any(mask):
            _fill_zero("empty window")
            return

        tw = time[mask]
        aw = accel[mask]
        sw = spd[mask]

        # --- Check operational speed range ---
        mean_spd = np.nanmean(sw)
        if not (min_spd <= mean_spd <= max_spd):
            _fill_zero(f"speed {mean_spd:.1f} out of range [{min_spd}-{max_spd}]")
            return

        # --- Compute jerk ---
        jerk = np.gradient(aw, tw)

        # --- Find negative and positive jerk peaks ---
        neg_idx = np.where(jerk < neg_thd)[0]
        pos_idx = np.where(jerk > pos_thd)[0]
        if len(neg_idx) == 0 or len(pos_idx) == 0:
            _fill_zero("no jerk peaks")
            return

        # --- Detect start/end of brake jerk ---
        i0 = detect_decel_onset(jerk, neg_thd)
        i1 = detect_brake_jerk_end(jerk, pos_thd, i0)
        if i0 is None:
            _fill_zero("no negative jerk start")
            return
        if i1 is None:
            _fill_zero("no positive recovery")
            return

        # --- Duration sanity check ---
        dur = tw[i1] - tw[i0]
        if dur <= 0 or dur > 0.5:
            _fill_zero(f"invalid duration {dur:.3f}")
            return

        # --- Compute metrics ---
        jerk_max  = np.max(np.abs(jerk[i0:i1+1]))
        accel_min = np.min(aw[i0:i1+1])

        # --- Record KPI results ---
        kpi_table.at[row_idx, "brakeJerkStart"] = safe_scalar(tw[i0])
        kpi_table.at[row_idx, "brakeJerkEnd"]   = safe_scalar(tw[i1])
        kpi_table.at[row_idx, "brakeJerkDur"]   = safe_scalar(dur)
        kpi_table.at[row_idx, "brakeJerkMax"]   = safe_scalar(jerk_max)
        kpi_table.at[row_idx, "brakeAccelMin"]  = safe_scalar(accel_min)

        print(
            f"   ✅ [Row {row_idx}] Brake jerk detected: "
            f"start={tw[i0]:.3f}s | end={tw[i1]:.3f}s | dur={dur:.3f}s | "
            f"jerkMax={jerk_max:.2f} | accelMin={accel_min:.2f} | spd={mean_spd:.1f} kph"
        )
