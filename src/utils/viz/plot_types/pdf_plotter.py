import numpy as np
from ..base_plotter import BasePlot

class PdfPlot(BasePlot):
    name = "pdf"

    def draw(self, ax, data):
        y = np.sort(data["y"])
        pct = np.linspace(0, 100, len(y))
        ax.plot(pct, y)

        if "threshold" in data:
            ax.axhline(data["threshold"], ls="--", color="black")

        ax.set_xlabel("% Distance")
        ax.set_ylabel("Value")
        ax.set_title("Distribution Curve")
        ax.grid(True)
