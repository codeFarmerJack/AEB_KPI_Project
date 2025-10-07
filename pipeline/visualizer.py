import os
import warnings
import pandas as pd
from utils.viz.scatter_plotter import scatter_plotter
# from utils.viz.stem_plotter import stem_plotter
# from utils.viz.pie_plotter import pie_plotter


class Visualizer:
    """
    Visualizer
    ----------
    Python equivalent of MATLAB Visualizer.
    Dispatches KPI visualization based on `graph_spec`.

    Works with:
      - Config (graphSpec, lineColors, markerShapes, calibratables, etc.)
      - KPIExtractor (path_to_chunks, kpi_table, etc.)
    """

    def __init__(self, config, kpi_extractor):
        if config is None or kpi_extractor is None:
            raise ValueError("Visualizer requires both Config and KPIExtractor instances.")

        # --- Validate Config structure ---
        required_cfg_attrs = ["graph_spec", "line_colors", "marker_shapes", "calibratables", "kpi_spec"]
        for attr in required_cfg_attrs:
            if not hasattr(config, attr):
                raise AttributeError(f"Config missing required attribute: {attr}")

        # --- Validate KPIExtractor ---
        if not hasattr(kpi_extractor, "path_to_chunks"):
            raise TypeError("kpi_extractor must have attribute 'path_to_chunks' (directory of CSVs).")

        # --- Core fields ---
        self.graph_spec = config.graph_spec
        self.line_colors = config.line_colors
        self.marker_shapes = config.marker_shapes
        self.calibratables = config.calibratables
        self.kpi_spec = config.kpi_spec
        self.path_to_kpi_schema = getattr(config, "kpi_schema_path", None)

        # --- Directories & CSVs ---
        self.path_to_chunks = kpi_extractor.path_to_chunks
        self.path_to_csv = os.path.join(self.path_to_chunks, "AEB_KPI_Results.csv")
        self.path_to_output = self.path_to_chunks
        # ✅ FIX: Initialize group counter for sequential figure numbering starting from 1
        self._group_counter = iter(range(1, 101))  # Generator: 1, 2, 3, ...

        # --- Load KPI data (optional but useful) ---
        if os.path.isfile(self.path_to_csv):
            try:
                self.kpi_data = pd.read_csv(self.path_to_csv)
                print(f"📄 Loaded KPI data from {self.path_to_csv}")
            except Exception as e:
                warnings.warn(f"⚠️ Failed to read {self.path_to_csv}: {e}")
                self.kpi_data = getattr(kpi_extractor, "kpi_table", pd.DataFrame())
        else:
            warnings.warn(f"⚠️ CSV not found at {self.path_to_csv}. Using in-memory KPI table.")
            self.kpi_data = getattr(kpi_extractor, "kpi_table", pd.DataFrame())

        # --- Validate ---
        if self.graph_spec is None or self.graph_spec.empty:
            warnings.warn("⚠️ graph_spec empty — no plots defined.")
        if self.kpi_spec is None or self.kpi_spec.empty:
            warnings.warn("⚠️ KPI spec missing or empty — variable names may not resolve properly.")

        self._fig_cache = {}

    # ------------------------------------------------------------------ #
    def plot(self):
        """Main dispatcher — loops through graph_spec rows."""
        if self.graph_spec is None or self.graph_spec.empty:
            warnings.warn("⚠️ No graph_spec found — skipping visualization.")
            return

        # Normalize column names
        self.graph_spec.columns = (
            self.graph_spec.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        # Drop "unnamed" columns (Excel leftovers)
        self.graph_spec = self.graph_spec.loc[:, ~self.graph_spec.columns.str.contains("^unnamed")]

        num_graphs = len(self.graph_spec)
        print(f"📊 Found {num_graphs} plot definitions in GraphSpec.")
        print("🎨 Launching visualization...\n")

        for j in range(1, num_graphs):
            plot_type = str(self.graph_spec.loc[j, "plottype"]).strip().lower()
            title = str(self.graph_spec.loc[j, "title"]).strip()
            print(f"🎨 Plotting [{plot_type.upper()}] at row {j} — Title: {title}")

            try:
                if plot_type == "scatter":
                    scatter_plotter(self, j)
                elif plot_type == "stem":
                    warnings.warn(f"⚙️ Stem plot at row {j} not yet implemented.")
                elif plot_type == "pie":
                    warnings.warn(f"⚙️ Pie plot at row {j} not yet implemented.")
                else:
                    warnings.warn(f"⚠️ Unsupported plot type '{plot_type}' at row {j}. Skipping.")

            except Exception as e:
                warnings.warn(f"⚠️ Plotting failed for row {j}: {e}")

        print("✅ Visualization complete.")
