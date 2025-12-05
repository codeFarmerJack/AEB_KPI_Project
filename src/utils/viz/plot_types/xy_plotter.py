from ..base_plotter import BasePlot


class XyPlotter(BasePlot):
    """
    Generic X-Y plotter for visualizing one KPI against another.
    
    Expected data dict:
    {
        "x": array,
        "y": array,
        "xlabel": "Distance (m)",        # optional
        "ylabel": "Lane Uncertainty",    # optional
        "title": "Lane Uncertainty vs Distance",  # optional
        "threshold": 0.4,                # optional
        "mode": "line"  # or "scatter"
    }
    """

    name = "xy"

    def draw(self, ax, data):
        x = data["x"]
        y = data["y"]

        mode = data.get("mode", "line")

        if mode == "scatter":
            ax.scatter(x, y, s=8, alpha=0.7)
        else:
            ax.plot(x, y, lw=0.6)

        # Optional threshold line
        if "threshold" in data:
            ax.axhline(
                data["threshold"],
                ls="--",
                color="black",
                linewidth=1.0
            )

        # Labels & title
        ax.set_xlabel(data.get("xlabel", "X"))
        ax.set_ylabel(data.get("ylabel", "Y"))
        ax.set_title(data.get("title", "X vs Y"))

        ax.grid(True)
