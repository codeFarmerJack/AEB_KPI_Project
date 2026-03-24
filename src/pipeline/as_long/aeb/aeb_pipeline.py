from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_long.aeb.aeb_event_segmenter import AebEventSegmenter
from src.pipeline.as_long.aeb.aeb_event_kpi_extractor import AebEventKpiExtractor
from src.pipeline.as_long.aeb.aeb_cycle_kpi_extractor import AebCycleKpiExtractor
from src.pipeline.as_long.aeb.aeb_event_visualizer import AebEventVisualizer


class AebPipeline(BasePipeline):
    """Pipeline orchestrator for AEB KPI extraction and visualization."""

    FEATURE_NAME = "AEB"
    SEGMENTER_CLS = AebEventSegmenter
    EVENT_EXTRACTOR_CLS = AebEventKpiExtractor
    CYCLE_EXTRACTOR_CLS = AebCycleKpiExtractor
    EVENT_VISUALIZER_CLS = AebEventVisualizer
