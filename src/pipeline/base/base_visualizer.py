import os
import warnings
import pandas as pd


class BaseVisualizer:
    """
    BaseVisualizer
    ---------------
    Provides shared infrastructure for KPI visualizers
    (AEB, FCW, ACC, etc.), without touching their plot() logic.
    """

    def __init__(self, config, kpi_extractor, feature: str):
        if config is None or kpi_extractor is None:
            raise ValueError("Visualizer requires both Config and KPIExtractor instances.")
        if feature is None:
            raise ValueError("Feature name (e.g. 'aeb', 'fcw') must be specified.")

        # --- Shared attributes ---
        self.feature         = feature.lower()
        self.config          = config
        self.in_path_results = kpi_extractor.out_path_results
        # -- Define output paths ---
        filename             = getattr(config, "kpi_result_filename", "kpi_results.xlsx")
        self.out_path_excel  = os.path.join(self.in_path_results, filename)
        self.out_path_output = os.path.join(self.in_path_results, self.feature)

        # --- Create output folder ---
        os.makedirs(self.out_path_output, exist_ok=True)

        # --- Shared config references ---
        self.graph_spec     = config.graph_spec.copy()
        self.line_colors    = config.line_colors
        self.marker_shapes  = config.marker_shapes
        self.calibratables  = config.calibratables
        self.event_kpi_list       = config.event_kpi_list
        # --- Load KPI sheet for this feature ---
        self.kpi_data       = self._load_kpi_data()
        # --- UI preference propagated to viz module ---
        self.interactive    = getattr(config, "interactive", False)

        print(f"✅ BaseVisualizer initialized for feature: {self.feature.upper()}")

    # --------------------------------------------------------------- #
    def _load_kpi_data(self):
        """Safely load KPI data for the given feature sheet."""
        if not os.path.isfile(self.out_path_excel):
            warnings.warn(f"⚠️ KPI Excel not found: {self.out_path_excel}")
            return getattr(self.config, "kpi_table", pd.DataFrame())

        try:
            df = pd.read_excel(self.out_path_excel, sheet_name=self.feature)
            print(f"📘 Loaded KPI data for feature '{self.feature}' — shape {df.shape}")
            return df
        except Exception as e:
            warnings.warn(f"⚠️ Failed to read '{self.feature}' sheet: {e}")
            return pd.DataFrame()

    # --------------------------------------------------------------- #
    def filter_graph_spec(self):
        """Return only rows of graph_spec relevant to this feature (and its common set)."""
        if self.graph_spec is None or self.graph_spec.empty:
            warnings.warn("⚠️ graph_spec is empty — cannot filter.")
            return pd.DataFrame()

        print("DEBUG graph_spec columns:", list(self.graph_spec.columns))

        # --- Normalize column names safely ---
        self.graph_spec.columns = (
            self.graph_spec.columns
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        if "feature" not in self.graph_spec.columns:
            warnings.warn("⚠️ No 'feature' column found in graph_spec — using all rows.")
            return self.graph_spec

        # --- Determine feature-specific common axis label ---
        common_label = f"common_{self.feature.lower()}"  # e.g., common_aeb, common_fcw, common_lsaeb, common_lka

        # --- Build mask: include rows for this feature or its specific common axis ---
        feature_vals = self.graph_spec["feature"].astype(str).str.strip().str.lower()
        mask = feature_vals.isin([self.feature, common_label])

        filtered = self.graph_spec.loc[mask].reset_index(drop=True)

        print(f"📊 Found {len(filtered)} plot rows for feature '{self.feature.upper()}' "
            f"(including '{common_label}' rows if present).")

        return filtered
