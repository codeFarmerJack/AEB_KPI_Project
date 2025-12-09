import numpy as np
import warnings

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor
from src.utils.signal_mdf import get_signal


class FcwCycleKpiExtractor(BaseCycleKpiExtractor):
    """
    Computes FCW availability KPI:
      - AvailDistPct: percentage of traveled distance where FCW is enabled
      - runSetting/inputHealthy/precondBlk/abort: distance-weighted condition percentages
    """

    FEATURE_NAME = "FCW"

    def __init__(self, input_handler, config):
        super().__init__(input_handler, config)

    def extract_cycle_kpis(self, mdf, fname):
        """
        Availability condition (mirrors AEB pattern):
            fcwPrecondBlk  == 0  
        Missing signals will be treated as permissive (healthy/precond/abort) with a warning.
        """
        try:
            time            = get_signal(mdf, "time", required=True)
            speed_mps       = get_signal(mdf, "egoSpeed", required=True)
            precond_blocked = get_signal(mdf, "fcwPrecondBlk", required=True)
        except AttributeError as e:
            warnings.warn(f"Missing required FCW signal: {e}")
            return {}

        # distance traveled per sample
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)

        dist       = speed_mps * dt
        total_dist = dist.sum()

        # Only keep overall availability
        kpi_keys = ["AvailDistPct"]

        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; FCW availability cannot be computed.")
            return {self.FEATURE_NAME: {k: 0.0 for k in kpi_keys}}

        cond_precond  = precond_blocked == 0
        avail_mask = cond_precond

        enabled_dist    = np.sum(dist[avail_mask])
        pct_avail       = enabled_dist / total_dist * 100
        metrics = {
            "AvailDistPct": round(pct_avail, 2),
        }

        return {self.FEATURE_NAME: {k: metrics.get(k, None) for k in kpi_keys}}
