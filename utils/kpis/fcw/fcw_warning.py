import numpy as np
import warnings
from utils.data_utils import safe_scalar


def fcw_warning(self, mdf, row_idx: int):
    """
    Extract TTC at the initial FCW warning trigger.

    Parameters
    ----------
    self : FcwKpiExtractor
        Instance of the KPI extractor (provides config thresholds & KPI table)
    mdf : SignalMDF
        MF4 chunk with signals (time, fcwTTC, fcwRequest, egoSpeedKph)
    row_idx : int
        Row index in the KPI table to update.
    """

    kpi_table = self.kpi_table

    # --- Extract signals ---
    try:
        time = np.asarray(mdf.time)
        ttc  = np.asarray(mdf.fcwTTC)
        lvl  = np.asarray(mdf.fcwSensitivity)
        fcw  = np.asarray(mdf.fcwRequest)
        spd  = np.asarray(mdf.egoSpeedKph)
    except AttributeError:
        warnings.warn("⚠️ Missing required FCW signals.")
        return

    # --- Ensure required columns exist ---
    cols = ["fcwSensitivityLvl", "fcwWarningTTC"]
    for c in cols:
        if c not in kpi_table.columns:
            kpi_table[c] = np.nan

    def _fill_nan(reason):
        for c in cols:
            kpi_table.at[row_idx, c] = np.nan
        print(f"   ⚠️ No FCW warning detected ({reason}) → filled NaN.")
        return

    # --- Detect FCW rising edge (2 → warning request) ---
    edges = np.where((fcw[:-1] < 2) & (fcw[1:] >= 2))[0]
    if len(edges) == 0:
        _fill_nan("no FCW trigger")
        return

    # --- Take the first FCW warning trigger ---
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
    kpi_table.at[row_idx, "fcwSensitivityLvl"]  = safe_scalar(lvl_warn)
    kpi_table.at[row_idx, "fcwWarningTTC"]      = safe_scalar(ttc_warn)



