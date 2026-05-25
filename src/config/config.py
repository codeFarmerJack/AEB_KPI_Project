"""Config data holder for KPI tool settings (loaded via ConfigLoader)."""

import warnings


class Config:
    """Holds parsed config data; use ConfigLoader for file I/O and parsing."""
    def __init__(self):
        self.signal_map = None       # vbRcSignals sheet
        self.event_kpi_list = None   # event KPI sheet
        self.cycle_kpi_list = None   # cycle KPI sheet
        self.graph_spec = None       # graphSpec sheet
        self.line_colors = None      # lineColors sheet
        self.marker_shapes = None    # markerShapes sheet
        self.calibratables = {}      # calibratables (optional)
        self.calibratables_interp = {}  # cached x/y arrays for interpolation
        self.params = None           # params sheet
        self.param_types = {}        # keep parameter type metadata
        self.kpi_excel_path = None
        self.kpi_excel_name = None
        self.domain_name = None
        self.kpi_result_filename = None
        self.signal_source = "roadcast_log"

    @classmethod
    def from_json(cls, json_config_path):
        """Create Config object from JSON file (supports both as_long & as_lat)."""
        from src.config.config_loader import ConfigLoader

        cfg = ConfigLoader.load(json_config_path)
        return cfg.validate()

    def validate(self):
        if self.signal_map is None:
            raise ValueError("signal_map is missing; check the KPI workbook 'vbRcSignals' sheet.")
        if self.event_kpi_list is None:
            warnings.warn("⚠️ event_kpi_list missing; event KPIs may be unavailable.")
        return self
