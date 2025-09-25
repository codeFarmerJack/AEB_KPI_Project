import json
import warnings
from pathlib import Path
import pandas as pd


class Config:
    def __init__(self):
        self.graph_spec = None
        self.line_colors = None
        self.marker_shapes = None
        self.calibratables = {}
        self.json_config_path = None
        self.project_root = ""
        self.signal_map = None
        self.signal_plot_spec_path = None
        self.signal_plot_spec_name = ""
        self.calibration_file_path = None
        self.calibration_file_name = ""
        self.kpi_schema_path = None
        self.kpi_schema_file_name = ""

    @classmethod
    def from_json(cls, json_config_path):
        """Create Config object from JSON file."""
        cfg = cls()
        cfg.json_config_path = str(json_config_path)

        config_struct = cls._load_config(json_config_path)

        # projectRoot
        if "projectRoot" in config_struct and "FilePath" in config_struct["projectRoot"]:
            project_root_path = config_struct["projectRoot"]["FilePath"]
            cfg.project_root = project_root_path or ""
        else:
            cfg.project_root = ""

        # KPI schema
        if "kpiSchema" in config_struct and "FilePath" in config_struct["kpiSchema"]:
            kpi_path = config_struct["kpiSchema"]["FilePath"]
            if kpi_path:
                cfg.kpi_schema_path = kpi_path
                cfg.kpi_schema_file_name = Path(kpi_path).name
            else:
                cfg.kpi_schema_path = ""
                cfg.kpi_schema_file_name = ""
        else:
            cfg.kpi_schema_path = ""
            cfg.kpi_schema_file_name = ""

        # SignalPlotSpec
        spec_path = config_struct["SignalPlotSpec"]["FilePath"]
        sheet_list = config_struct["SignalPlotSpec"]["Sheets"]
        signal_map_plot_spec = cls._load_signal_map_plot_spec(spec_path, sheet_list)

        cfg.signal_map = signal_map_plot_spec.get("vbRcSignals")
        cfg.graph_spec = signal_map_plot_spec.get("graphSpec")
        cfg.line_colors = signal_map_plot_spec.get("lineColors")
        cfg.marker_shapes = signal_map_plot_spec.get("markerShapes")
        cfg.signal_plot_spec_path = spec_path
        cfg.signal_plot_spec_name = Path(spec_path).name

        # Calibration
        calib_file = config_struct["Calibration"]["FilePath"]
        sheet_defs = config_struct["Calibration"]["Sheets"]
        cfg.calibratables = cls._load_calibratables(calib_file, sheet_defs)
        cfg.calibration_file_path = calib_file
        cfg.calibration_file_name = Path(calib_file).name

        return cfg

    # --------------------
    # Helpers
    # --------------------
    @staticmethod
    def _load_config(file_path):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            params = json.load(f)

        if "SignalPlotSpec" not in params or "FilePath" not in params["SignalPlotSpec"]:
            raise ValueError("Missing SignalPlotSpec.FilePath in config.")
        if "Sheets" not in params["SignalPlotSpec"]:
            raise ValueError("SignalPlotSpec.Sheets must be defined in config.")

        if "Calibration" not in params or "FilePath" not in params["Calibration"]:
            raise ValueError("Missing Calibration.FilePath in config.")
        if "Sheets" not in params["Calibration"]:
            raise ValueError("Calibration.Sheets must be defined in config.")

        return params

    @staticmethod
    def _load_signal_map_plot_spec(file_path, sheet_list):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"SignalPlotSpec file not found: {file_path}")

        result = {}
        for sheet_name in sheet_list:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                result[sheet_name] = df
            except Exception as e:
                warnings.warn(f'Failed to read sheet "{sheet_name}": {e}')
        return result

    @staticmethod
    def _load_calibratables(calib_file, sheet_map):
        file_path = Path(calib_file)
        if not file_path.exists():
            raise FileNotFoundError(f"Calibration file not found: {file_path}")

        calibratables = {}
        for sheet, cal_defs in sheet_map.items():
            for cal_name, excel_range in cal_defs.items():
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    calibratables[cal_name] = df
                except Exception as e:
                    warnings.warn(
                        f'Failed to load "{cal_name}" from sheet "{sheet}" range "{excel_range}": {e}'
                    )
                    calibratables[cal_name] = None
        return calibratables
