from src.viz.visualizers.event_visualizer import BaseEventVisualizer


class LsaebEventVisualizer(BaseEventVisualizer):
    """LSAEB KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="lsaeb")
