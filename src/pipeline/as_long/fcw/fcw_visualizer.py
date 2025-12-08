from src.viz.visualizers.event_visualizer import EventVisualizer


class FcwVisualizer(EventVisualizer):
    """FCW KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="fcw")
