from typing import Type, Optional

from src.viz.plotters.scatter_plotter import ScatterPlotter
from src.viz.plotters.line_plotter import LinePlotter
from src.viz.plotters.bar_plotter import BarPlotter
from src.viz.plotters.box_plotter import BoxPlotter
from src.viz.plotters.heatmap_plotter import HeatmapPlotter
from src.viz.plotters.map_plotter import MapPlotter

_REGISTRY = {
    "scatter": ScatterPlotter,
    "line": LinePlotter,
    "bar": BarPlotter,
    "box": BoxPlotter,
    "heatmap": HeatmapPlotter,
    "map": MapPlotter,
}


def get_plotter_class(plot_type: str) -> Optional[Type]:
    return _REGISTRY.get(str(plot_type).lower())
