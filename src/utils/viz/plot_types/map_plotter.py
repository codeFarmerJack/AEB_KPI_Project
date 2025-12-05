import numpy as np
from ..base_plotter import BasePlot

class MapPlot(BasePlot):
    name = "map"

    def draw(self, ax, data):
        lon = data["lon"]
        lat = data["lat"]

        ax.plot(lon, lat, "-", lw=1, color="steelblue")

        if "supp_idx" in data:
            idx = data["supp_idx"]
            ax.scatter(lon[idx], lat[idx], s=10, color='red')

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Vehicle Path")
        ax.grid(True)
