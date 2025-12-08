from src.viz.visualizers.event_visualizer import EventVisualizer


class LkaVisualizer(EventVisualizer):
    """LKA KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="lka")
