import warnings

from src.viz.plotters.scatter_plotter import ScatterPlotter


class LinePlotter(ScatterPlotter):
    """
    Thin wrapper over ScatterPlotter that always connects points.

    The graph_spec contract stays the same as scatter:
    - row 0 defines the X axis meta (reference/min/max/label)
    - subsequent rows define Y series to plot
    """

    def __init__(self, visualizer):
        super().__init__(visualizer)

    def plot_row(self, graph_idx: int) -> None:
        """Defer to ScatterPlotter but force 'connectpoints' on."""
        try:
            # monkey-patch the connect flag before plotting
            original = self.graph_spec.loc[graph_idx, "connectpoints"]
            self.graph_spec.loc[graph_idx, "connectpoints"] = True
            super().plot_row(graph_idx)
        finally:
            # restore original value to avoid side-effects on other plotters
            try:
                self.graph_spec.loc[graph_idx, "connectpoints"] = original
            except Exception:
                warnings.warn(
                    f"⚠️ Could not restore connect flag for row {graph_idx}; "
                    "graph_spec may have been modified in-place."
                )
