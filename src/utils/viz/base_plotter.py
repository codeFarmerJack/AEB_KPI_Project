class BasePlot:
    """
    Abstract base class for all KPI visualization plotters.

    Every subclass must implement:
        - name (string identifier used in PLOT_REGISTRY)
        - draw(ax, data)

    Parameters to draw():
        ax   : matplotlib Axes object
        data : dict containing all data and metadata needed for drawing

    This ensures a consistent interface for all plotters used by the Dashboard.
    """

    # Identifier used when registering the plotter in PLOT_REGISTRY
    name = "base"

    def draw(self, ax, data):
        """
        Draw the plot on the given axes.

        Subclasses must override this method.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Axis to draw on.
        data : dict
            Data needed for drawing the plot.
        """

        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the draw(ax, data) method."
        )
