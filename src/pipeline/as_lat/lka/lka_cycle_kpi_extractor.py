import numpy as np
import warnings
from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor

class LkaCycleKpiExtractor(BaseCycleKpiExtractor):
    """
    Computes LKA feature availability KPIs:
      - AvailDistPctLeft
      - AvailDistPctRight
    """

    FEATURE_NAME = "LKA"

    def __init__(self, input_handler, config):
        super().__init__(input_handler, config)

    def extract_cycle_kpis(self, mdf, fname):
        try:
            time        = np.asarray(mdf.time)
            speed_mps   = np.asarray(mdf.egoSpeed)
            ready_left  = np.asarray(mdf.lkaReadyLeft)
            ready_right = np.asarray(mdf.lkaReadyRight)
            lka_block   = np.asarray(mdf.lkaPrecondBlk)
            lka_abort   = np.asarray(mdf.lkaAbort)
        except AttributeError as e:
            warnings.warn(f"Missing required LKA signal: {e}")
            return {}

        # ------------------------------------------------------------
        # Normalize schema to avoid future KeyError issues
        # ------------------------------------------------------------
        schema = self.config.cycle_kpi_list.copy()
        schema.columns = schema.columns.str.strip().str.lower()

        features = [
            f for f in schema["feature"].unique()
            if f.lower() != "common"
        ]

        # -----------------------------
        # distance per sample
        # -----------------------------
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)

        dist       = speed_mps * dt
        total_dist = dist.sum()

        # Zero distance → return zeros for all features
        if total_dist <= 0:
            return {
                feature: {
                    "AvailDistPctLeft":  0.0,
                    "AvailDistPctRight": 0.0
                }
                for feature in features
            }

        # -----------------------------
        # availability conditions
        # -----------------------------
        global_ok   = (lka_block == 0) & (lka_abort == 0)
        avail_left  = (ready_left == 1) & global_ok
        avail_right = (ready_right == 1) & global_ok

        pct_left  = np.sum(dist[avail_left])  / total_dist * 100
        pct_right = np.sum(dist[avail_right]) / total_dist * 100

        # -----------------------------
        # Build output for ALL features
        # -----------------------------
        return {
            feature: {
                "AvailDistPctLeft":  round(pct_left, 2),
                "AvailDistPctRight": round(pct_right, 2),
            }
            for feature in features
        }


