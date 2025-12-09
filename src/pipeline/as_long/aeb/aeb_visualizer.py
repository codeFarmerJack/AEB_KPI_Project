from src.viz.visualizers.event_visualizer import BaseEventVisualizer
from src.viz.visualizers.cycle_visualizer import BaseCycleVisualizer


class AebCycleVisualizer(BaseCycleVisualizer):
    """
    Feature-specific cycle visualizer for AEB.
    Currently inherits the base layout; override plot_cycle for custom layouts.
    """
    def __init__(self, out_dir: str):
        super().__init__(out_dir)


class AebEventVisualizer(BaseEventVisualizer):
    """AEB KPI visualizer routed through the shared viz module."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="aeb")
