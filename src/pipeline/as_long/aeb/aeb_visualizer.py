from src.viz.visualizers.event_visualizer import EventVisualizer


class AebVisualizer(EventVisualizer):
    """AEB KPI visualizer routed through the shared viz module."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")
