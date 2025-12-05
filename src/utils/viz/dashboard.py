import matplotlib.pyplot as plt
from .registry import PLOT_REGISTRY


class Dashboard:
    """
    A flexible grid-based dashboard for plotting KPIs using registered plotters.
    """

    def __init__(self, rows, cols, figsize=(18, 10)):
        self.rows = rows
        self.cols = cols
        self.fig = plt.figure(figsize=figsize)
        self.gs = self.fig.add_gridspec(rows, cols)
        self.components = []   # list of (row, col, rowspan, colspan, plot_instance, data)

    def add(self, row, col, plot, data, rowspan=1, colspan=1):
        """
        Add a plot to the dashboard.

        Parameters
        ----------
        row : int
            Starting grid row
        col : int
            Starting grid column
        plot : str or BasePlot instance
            - If str: must match a key in PLOT_REGISTRY, e.g. "map", "xy", "bar"
            - If object: must be an instantiated subclass of BasePlot
        data : dict
            Data payload passed to the plotter's draw(ax, data)
        rowspan : int
            How many grid rows this plot spans
        colspan : int
            How many grid columns this plot spans
        """

        # If the user passed a string, we look it up in the registry
        if isinstance(plot, str):
            if plot not in PLOT_REGISTRY:
                raise KeyError(f"Plot type '{plot}' is not registered. "
                               f"Valid types: {list(PLOT_REGISTRY.keys())}")
            plot = PLOT_REGISTRY[plot]()  # instantiate the plotter

        # Add plot component
        self.components.append((row, col, rowspan, colspan, plot, data))

    def render(self, tight=True):
        """
        Render all plots onto the dashboard figure.
        """

        for row, col, rowspan, colspan, plot, data in self.components:
            ax = self.fig.add_subplot(self.gs[row:row + rowspan, col:col + colspan])

            # Draw the plot
            plot.draw(ax, data)

        if tight:
            self.fig.tight_layout()

        return self.fig
