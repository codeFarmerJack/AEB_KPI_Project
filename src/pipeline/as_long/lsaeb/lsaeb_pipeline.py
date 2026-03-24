from src.pipeline.base.base_pipeline import BasePipeline
from src.pipeline.as_long.lsaeb.lsaeb_event_segmenter import LsaebEventSegmenter
from src.pipeline.as_long.lsaeb.lsaeb_event_kpi_extractor import LsaebEventKpiExtractor
from src.pipeline.as_long.lsaeb.lsaeb_visualizer import LsaebEventVisualizer


class LsaebPipeline(BasePipeline):
    """Pipeline orchestrator for LSAEB KPI extraction and visualization."""

    FEATURE_NAME = "LSAEB"
    SEGMENTER_CLS = LsaebEventSegmenter
    EVENT_EXTRACTOR_CLS = LsaebEventKpiExtractor
    EVENT_VISUALIZER_CLS = LsaebEventVisualizer
