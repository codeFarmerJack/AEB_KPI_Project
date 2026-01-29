import numpy as np
import pandas as pd
import warnings

from src.utils.signal_mdf import get_signal


class AebImpactRelSpeedCalculator:
    """
    Computes ImpactRelSpdKph during AEB events.

    Condition:
      - (aebPartialState == 2 OR aebFullState == 2)
      - longGap transitions from >= 1 to < 1 between samples n and n+1
    Relative speed is evaluated at sample n+1 (first below 1).
    """

    def __init__(self, extractor):
        """Initialize from parent AebEventKpiExtractor instance."""
        pass  # no attributes needed

    def compute_impact_rel_speed(self, mdf, kpi_table, row_idx):
        col = "ImpactRelSpdKph"
        if col not in kpi_table.columns:
            kpi_table[col] = pd.Series([np.nan] * len(kpi_table), dtype="float")

        print(f"🧪 [Row {row_idx}] ImpactRelSpdKph debug: start")
        long_gap = get_signal(mdf, "longGap")
        aeb_partial = get_signal(mdf, "aebPartialState")
        aeb_full = get_signal(mdf, "aebFullState")
        ego_spd = get_signal(mdf, "egoSpeedKph")
        tgt_spd = get_signal(mdf, "objSpeedKph")

        if tgt_spd is None:
            tgt_spd_ms = get_signal(mdf, "objSpeed")
            if tgt_spd_ms is not None:
                tgt_spd = np.asarray(tgt_spd_ms, dtype=float) * 3.6
                print(f"🧪 [Row {row_idx}] ImpactRelSpdKph debug: using objSpeed (m/s) -> kph")

        required = {
            "longGap": long_gap,
            "aebPartialState": aeb_partial,
            "aebFullState": aeb_full,
            "egoSpeedKph": ego_spd,
            "objSpeedKph": tgt_spd,
        }
        missing = [name for name, sig in required.items() if sig is None]
        if missing:
            print(f"🧪 [Row {row_idx}] ImpactRelSpdKph debug: missing {missing}")
            warnings.warn(f"[Row {row_idx}] Missing required signal(s): {', '.join(missing)}")
            kpi_table.at[row_idx, col] = np.nan
            return

        lengths = [len(sig) for sig in required.values()]
        min_len = min(lengths) if lengths else 0
        if min_len < 2:
            print(f"🧪 [Row {row_idx}] ImpactRelSpdKph debug: min_len={min_len}, lengths={lengths}")
            warnings.warn(f"[Row {row_idx}] ImpactRelSpdKph: insufficient samples (min_len={min_len})")
            kpi_table.at[row_idx, col] = np.nan
            return

        long_gap = np.asarray(long_gap[:min_len], dtype=float)
        aeb_partial = np.asarray(aeb_partial[:min_len], dtype=float)
        aeb_full = np.asarray(aeb_full[:min_len], dtype=float)
        ego_spd = np.asarray(ego_spd[:min_len], dtype=float)
        tgt_spd = np.asarray(tgt_spd[:min_len], dtype=float)

        gap_cross = (long_gap[:-1] >= 1.0) & (long_gap[1:] < 1.0)
        state_active = (aeb_partial[:-1] == 2) | (aeb_full[:-1] == 2)
        idxs = np.where(state_active & gap_cross)[0]

        if idxs.size == 0:
            print(
                f"🧪 [Row {row_idx}] ImpactRelSpdKph debug: no idxs "
                f"(gap_cross={int(gap_cross.sum())}, state_active={int(state_active.sum())})"
            )
            kpi_table.at[row_idx, col] = np.nan
            return

        impact_idx = int(idxs[0] + 1)
        rel_spd = ego_spd[impact_idx] - tgt_spd[impact_idx]
        print(
            f"🧪 [Row {row_idx}] ImpactRelSpdKph debug: impact_idx={impact_idx}, "
            f"ego={ego_spd[impact_idx]:.3f}, tgt={tgt_spd[impact_idx]:.3f}, rel={rel_spd:.3f}"
        )
        kpi_table.at[row_idx, col] = rel_spd if np.isfinite(rel_spd) else np.nan
