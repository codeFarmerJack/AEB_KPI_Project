import numpy as np
import warnings
from utils.data_utils import safe_scalar


class FcwWarningCalculator:
    """
    Extracts TTC and sensitivity level at the initial FCW warning trigger.

    Detects the first FCW warning event (fcwRequest rising to level 2) and records:
      • fcwSensitivityLvl - sensitivity level at trigger
      • fcwWarningTTC     - TTC value at trigger

    Updates the KPI table in place.
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize using parameters from the parent FcwKpiExtractor instance.
        """
        # placeholder for future parameters
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_fcw_warning(self, mdf, kpi_table, row_idx: int):
        """
        Extract TTC and sensitivity level at the first FCW warning trigger.

        Parameters
        ----------
        mdf : SignalMDF
            MF4 chunk with signals (time, fcwTTC, fcwRequest, fcwSensitivity, egoSpeedKph)
        kpi_table : pd.DataFrame
            The KPI table to update in place.
        row_idx : int
            Row index in the KPI table.
        """

        # --- Ensure KPI columns exist ---
        cols = ["fcwSensitivityLvl", "fcwWarningTTC"]
        for c in cols:
            if c not in kpi_table.columns:
                kpi_table[c] = np.nan

        def _fill_nan(reason: str):
            """Fill NaN directly into KPI table."""
            for c in cols:
                kpi_table.at[row_idx, c] = np.nan
            print(f"   ⚠️ [Row {row_idx}] No FCW warning detected ({reason}) → filled NaN.")
            return

        # --- Extract required signals ---
        try:
            time = np.asarray(mdf.time)
            ttc  = np.asarray(mdf.fcwTTC)
            lvl  = np.asarray(mdf.fcwSensitivity)
            fcw  = np.asarray(mdf.fcwRequest)
            spd  = np.asarray(mdf.egoSpeedKph)
        except AttributeError:
            _fill_nan("missing required FCW signals")
            return

        # --- Detect FCW rising edge (2 → warning trigger) ---
        edges = np.where((fcw[:-1] < 2) & (fcw[1:] >= 2))[0]
        if len(edges) == 0:
            _fill_nan("no FCW trigger")
            return

        # --- Take first trigger sample ---
        idx_warn = edges[0] + 1
        t_warn   = time[idx_warn]
        ttc_warn = ttc[idx_warn] if idx_warn < len(ttc) else np.nan
        lvl_warn = lvl[idx_warn] if idx_warn < len(lvl) else np.nan
        spd_warn = spd[idx_warn] if idx_warn < len(spd) else np.nan

        # --- Sanity checks ---
        if np.isnan(ttc_warn) or ttc_warn <= 0 or ttc_warn > 10:
            _fill_nan(f"invalid TTC value ({ttc_warn})")
            return

        # --- Record KPI results ---
        kpi_table.at[row_idx, "fcwSensitivityLvl"] = safe_scalar(lvl_warn)
        kpi_table.at[row_idx, "fcwWarningTTC"]     = safe_scalar(ttc_warn)

        # Optional: you can include debug print if desired
        #print(
        #    f"   ✅ [Row {row_idx}] FCW warning detected: "
        #    f"time={t_warn:.3f}s | TTC={ttc_warn:.2f}s | "
        #    f"SensLvl={lvl_warn:.1f} | spd={spd_warn:.1f} kph"
        #)
