from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_long.fcw.fcw_event_segmenter import FcwEventSegmenter
from src.pipeline.as_long.fcw.fcw_event_kpi_extractor import FcwEventKpiExtractor
from src.pipeline.as_long.fcw.fcw_cycle_kpi_extractor import FcwCycleKpiExtractor

from src.pipeline.as_long.fcw.fcw_event_visualizer import FcwEventVisualizer


class FcwPipeline(BasePipeline):
    """Pipeline orchestrator for FCW KPI extraction and visualization."""

    FEATURE_NAME = "FCW"
    SEGMENTER_CLS = FcwEventSegmenter
    EVENT_EXTRACTOR_CLS = FcwEventKpiExtractor
    CYCLE_EXTRACTOR_CLS = FcwCycleKpiExtractor
    EVENT_VISUALIZER_CLS = FcwEventVisualizer
