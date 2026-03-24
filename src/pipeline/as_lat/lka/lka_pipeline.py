from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_lat.lka.lka_event_segmenter import LkaEventSegmenter
from src.pipeline.as_lat.lka.lka_event_kpi_extractor import LkaEventKpiExtractor
from src.pipeline.as_lat.lka.lka_cycle_kpi_extractor import LkaCycleKpiExtractor
from src.pipeline.as_lat.lka.lka_event_visualizer import LkaEventVisualizer


class LkaPipeline(BasePipeline):
    """Pipeline orchestrator for LKA KPI extraction and visualization."""

    FEATURE_NAME = "LKA"
    SEGMENTER_CLS = LkaEventSegmenter
    EVENT_EXTRACTOR_CLS = LkaEventKpiExtractor
    CYCLE_EXTRACTOR_CLS = LkaCycleKpiExtractor
    EVENT_VISUALIZER_CLS = LkaEventVisualizer
