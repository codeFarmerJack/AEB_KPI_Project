import numpy as np
import warnings

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor


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
            fcwRunSetting == 2
            AND aebInputHealthy == 1 (if available)
            AND fcwPrecondBlk  == 0  (if available)
            AND fcwAbort       == 0  (if available)
        Missing signals will be treated as permissive (healthy/precond/abort) with a warning.
        """
        try:
            time        = np.asarray(mdf.time)
            speed_mps   = np.asarray(mdf.egoSpeed)
            run_setting = np.asarray(mdf.fcwRunSetting)
        except AttributeError as e:
            warnings.warn(f"Missing required FCW signal: {e}")
            return {}

        # Optional signals with permissive defaults
        def _safe_bool(sig_name, default_val):
            try:
                return np.asarray(getattr(mdf, sig_name))
            except AttributeError:
                warnings.warn(f"ℹ️ Optional FCW signal '{sig_name}' missing; assuming {default_val}.")
                return np.full_like(run_setting, default_val)

        input_healthy   = _safe_bool("aebInputHealthy", 1)
        precond_blocked = _safe_bool("fcwPrecondBlk", 0)
        fcw_abort       = _safe_bool("fcwAbort", 0)

        # distance traveled per sample
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)

        dist       = speed_mps * dt
        total_dist = dist.sum()

        # Determine KPI column names from schema (fallback defaults)
        kpi_names = self.get_feature_kpi_names(self.FEATURE_NAME)
        default_names = ["AvailDistPct", "runSetting", "inputHealthy", "precondBlk", "abort"]
        kpi_keys = kpi_names if kpi_names else default_names

        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; FCW availability cannot be computed.")
            return {self.FEATURE_NAME: {k: 0.0 for k in kpi_keys}}

        cond_run      = run_setting == 2
        cond_healthy  = input_healthy == 1
        cond_precond  = precond_blocked == 0
        cond_abort_ok = fcw_abort == 0

        avail_mask = cond_run & cond_healthy & cond_precond & cond_abort_ok

        enabled_dist    = np.sum(dist[avail_mask])
        pct_avail       = enabled_dist / total_dist * 100
        pct_run         = np.sum(dist[cond_run]) / total_dist * 100
        pct_healthy     = np.sum(dist[cond_healthy]) / total_dist * 100
        pct_precond     = np.sum(dist[cond_precond]) / total_dist * 100
        pct_abort_ok    = np.sum(dist[cond_abort_ok]) / total_dist * 100

        samples_total   = len(dist)
        samples_enabled = int(np.sum(avail_mask))

        # Debug diagnostics
        def _count(mask):
            return int(np.sum(mask))
        print(
            f"[FCW cycle] total_dist={total_dist:.2f}, enabled_dist={enabled_dist:.2f}, "
            f"samples_total={samples_total}, samples_enabled={samples_enabled}"
        )
        print(
            f"   ├─ fcwRunSetting==2: {_count(cond_run)} "
            f"| fcwInputHealthy==1: {_count(cond_healthy)} "
            f"| fcwPrecondBlk==0: {_count(cond_precond)} "
            f"| fcwAbort==0: {_count(cond_abort_ok)}"
        )

        metrics = {
            "AvailDistPct": round(pct_avail, 2),
            "runSetting": round(pct_run, 2),
            "inputHealthy": round(pct_healthy, 2),
            "precondBlk": round(pct_precond, 2),
            "abort": round(pct_abort_ok, 2),
        }

        return {self.FEATURE_NAME: {k: metrics.get(k, None) for k in kpi_keys}}
