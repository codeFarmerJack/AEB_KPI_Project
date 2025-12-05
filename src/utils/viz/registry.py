from .plot_types.map_plotter import MapPlotter
from .plot_types.bar_plotter import BarPlotter
from .plot_types.box_plotter import BoxPlotter
from .plot_types.hbar_plotter import HBarPlotter
from .plot_types.pdf_plotter import PdfPlotter
from .plot_types.pie_plotter import PiePlotter
from .plot_types.xy_plotter import XyPlotter


PLOT_REGISTRY = {
    "map": MapPlotter,
    "bar": BarPlotter,
    "box": BoxPlotter,
    "hbar": HBarPlotter,
    "pdf": PdfPlotter,       
    "pie": PiePlotter,
    "xy": XyPlotter,         # generalized 2-signal plot
}
