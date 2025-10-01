import os
import warnings
from utils.viz.scatter_plotter import ScatterPlotter
# from utils.viz.stem_plotter import StemPlotter   # placeholder
# from utils.viz.pie_plotter import PiePlotter     # placeholder


class Visualizer:
    """
    Visualizer: dispatcher for plotting KPI results.
    """

    def __init__(self, config, kpi_extractor):
        """
        Initialize Visualizer from config and KPIExtractor.
        """
        if config is None or kpi_extractor is None:
            raise ValueError("Configuration object and KPIExtractor instance are required.")

        # Validate KPIExtractor type
        if not hasattr(kpi_extractor, "path_to_csv"):
            raise TypeError("Second argument must be a KPIExtractor-like instance with path_to_csv.")

        # Mirror config
        self.graph_spec = config.graph_spec
        self.line_colors = config.lineColors
        self.marker_shapes = config.markerShapes
        self.calibratables = config.calibratables
        self.path_to_kpi_schema = config.kpiSchemaPath
        self.path_to_csv = kpi_extractor.path_to_csv

    def plot(self):
        """Main plotting dispatcher using path_to_csv."""
        if not self.path_to_csv or not os.path.isdir(self.path_to_csv):
            warnings.warn(f"Invalid or empty path_to_csv: {self.path_to_csv}. Plotting aborted.")
            return

        num_graphs = len(self.graph_spec)

        for j in range(1, num_graphs):  # MATLAB skipped row 1 → start at index 1
            plot_type = str(self.graph_spec.loc[j, "plotType"]).strip().lower()

            if plot_type == "scatter":
                plotter = ScatterPlotter(
                    self.graph_spec,
                    self.line_colors,
                    self.marker_shapes,
                    self.calibratables,
                    self.path_to_csv,
                    self.path_to_kpi_schema,
                )
                plotter.plot(j)

            elif plot_type == "stem":
                # Placeholder
                print(f"[StemPlotter] row {j} not yet implemented.")

            elif plot_type == "pie":
                # Placeholder
                print(f"[PiePlotter] row {j} not yet implemented.")

            else:
                warnings.warn(f"Unsupported plot type '{plot_type}' at row {j}. Skipping.")
