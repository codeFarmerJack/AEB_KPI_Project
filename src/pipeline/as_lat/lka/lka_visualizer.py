from src.viz.visualizers.base_event_visualizer import BaseEventVisualizer


class LkaEventVisualizer(BaseEventVisualizer):
    """LKA KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="lka")
