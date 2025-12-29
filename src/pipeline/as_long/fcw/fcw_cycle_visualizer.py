from src.viz.visualizers.base_cycle_visualizer import BaseCycleVisualizer


class FcwCycleVisualizer(BaseCycleVisualizer):
    """Feature-specific cycle visualizer for FCW."""

    def __init__(self, out_dir: str):
        super().__init__(out_dir)
