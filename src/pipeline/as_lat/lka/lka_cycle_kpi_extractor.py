from src.pipeline.base.rule_based_cycle_kpi_extractor import RuleBasedCycleKpiExtractor
from src.pipeline.as_lat.lka.lka_cycle_visualizer import LkaCycleVisualizer


class LkaCycleKpiExtractor(RuleBasedCycleKpiExtractor):
    """
    Computes LKA feature availability KPIs:
      - AvailDistPctLeft
      - AvailDistPctRight
    """

    FEATURE_NAME = "LKA"
    CYCLE_VISUALIZER_CLS = LkaCycleVisualizer
    OUTPUT_FEATURE_MODE = "schema"
    SIGNAL_SPECS = {
        "time": {"signal": "time"},
        "speed_mps": {"signal": "egoSpeed"},
        "ready_left": {"signal": "lkaReadyLeft"},
        "ready_right": {"signal": "lkaReadyRight"},
        "lka_block": {"signal": "lkaPrecondBlk"},
        "lka_abort": {"signal": "lkaAbort"},
    }
    METRIC_SPECS = (
        {
            "key": "AvailDistPctLeft",
            "mask": lambda signals: (
                (signals.ready_left == 1)
                & (signals.lka_block == 0)
                & (signals.lka_abort == 0)
            ),
        },
        {
            "key": "AvailDistPctRight",
            "mask": lambda signals: (
                (signals.ready_right == 1)
                & (signals.lka_block == 0)
                & (signals.lka_abort == 0)
            ),
        },
    )
