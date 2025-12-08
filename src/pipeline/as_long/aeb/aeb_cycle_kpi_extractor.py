import numpy as np
import warnings

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor


class AebCycleKpiExtractor(BaseCycleKpiExtractor):
    """
    Computes AEB availability KPI:
      - AvailDistPct: percentage of traveled distance where AEB is available
    """

    FEATURE_NAME = "AEB"

    def __init__(self, input_handler, config):
        super().__init__(input_handler, config)

    def extract_cycle_kpis(self, mdf, fname):
        """
        Availability condition:
            aebRunSetting == 2
            AND aebInputHealthy == 1
            AND aebPrecondBlk  == 0
            AND aebAbort       == 0
        """
        try:
            time            = np.asarray(mdf.time)
            speed_mps       = np.asarray(mdf.egoSpeed)
            run_setting     = np.asarray(mdf.aebRunSetting)
            input_healthy   = np.asarray(mdf.aebInputHealthy)
            precond_blocked = np.asarray(mdf.aebPrecondBlk)
            aeb_abort       = np.asarray(mdf.aebAbort)
        except AttributeError as e:
            warnings.warn(f"Missing required AEB signal: {e}")
            return {}

        # distance traveled per sample
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)

        dist       = speed_mps * dt
        total_dist = dist.sum()

        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; availability cannot be computed.")
            return {self.FEATURE_NAME: {"AvailDistPct": 0.0}}

        cond_run      = run_setting == 2
        cond_healthy  = input_healthy == 1
        cond_precond  = precond_blocked == 0
        cond_abort_ok = aeb_abort == 0

        avail_mask = cond_run & cond_healthy & cond_precond & cond_abort_ok

        enabled_dist    = np.sum(dist[avail_mask])
        pct_avail       = enabled_dist / total_dist * 100
        samples_total   = len(dist)
        samples_enabled = int(np.sum(avail_mask))

        # Debug diagnostics
        print(
            f"[AEB cycle] total_dist={total_dist:.2f}, enabled_dist={enabled_dist:.2f}, "
            f"samples_total={samples_total}, samples_enabled={samples_enabled}"
        )
        # Condition-level diagnostics
        def _count(mask):
            return int(np.sum(mask))
        print(
            f"   ├─ aebRunSetting==2: {_count(cond_run)} "
            f"| aebInputHealthy==1: {_count(cond_healthy)} "
            f"| aebPrecondBlk==0: {_count(cond_precond)} "
            f"| aebAbort==0: {_count(cond_abort_ok)}"
        )

        # Determine KPI column name from schema (fallback to AvailDistPct)
        kpi_names = self.get_feature_kpi_names(self.FEATURE_NAME)
        kpi_name = kpi_names[0] if kpi_names else "AvailDistPct"

        # Return KPI dict keyed by this feature only
        return {self.FEATURE_NAME: {kpi_name: round(pct_avail, 2)}}
