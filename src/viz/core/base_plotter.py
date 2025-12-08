# src/viz/core/base_plotter.py
from abc import ABC, abstractmethod
import pandas as pd


class BasePlotter(ABC):
    """
    Base interface for all plotters (scatter, line, bar, map, ...).

    A Plotter is intentionally dumb:
    - it receives a 'visualizer context' (BaseVisualizer subclass)
    - it receives one row from graph_spec
    - it draws its series on the given figure/axes.
    """

    def __init__(self, visualizer):
        if visualizer is None:
            raise ValueError("Plotter requires a visualizer context.")
        self.viz = visualizer  # BaseVisualizer (or subclass)
        if not isinstance(self.viz.kpi_data, pd.DataFrame):
            raise ValueError("Visualizer must provide kpi_data as a DataFrame.")

    @abstractmethod
    def plot_row(self, row_idx: int) -> None:
        """
        Plot the graph row with index 'row_idx' from viz.graph_spec.
        """
        raise NotImplementedError
