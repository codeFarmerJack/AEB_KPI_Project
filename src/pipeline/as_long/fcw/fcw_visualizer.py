from src.viz.visualizers.base_event_visualizer import BaseEventVisualizer
from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer


class FcwCycleVisualizer(BaseCycleVisualizer):
    """Feature-specific cycle visualizer for FCW."""

    def __init__(self, out_dir: str):
        super().__init__(out_dir)


class FcwEventVisualizer(BaseEventVisualizer):
    """FCW KPI visualizer."""

    def __init__(self, config, kpi_extractor):
        super().__init__(config, kpi_extractor, feature="fcw")
