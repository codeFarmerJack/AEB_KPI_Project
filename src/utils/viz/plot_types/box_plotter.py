import numpy as np
from ..base_plot import BasePlot


class BoxPlotter(BasePlot):
    """
    Box plot for distribution visualization.

    Expected data dict:
    {
        "values": array-like,
        "title": "Optional title",
        "ylabel": "Optional ylabel",
        "show_median_line": True or False
    }
    """

    name = "box"

    def draw(self, ax, data):
        values = data["values"]

        ax.boxplot(values)

        # optional median line
        if data.get("show_median_line", True):
            median = np.median(values)
            ax.axhline(median, ls="--", color="black")

        ax.set_title(data.get("title", "Box Plot"))
        ax.set_ylabel(data.get("ylabel", "Value"))
        ax.grid(True)
