import json
import warnings
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook


class Config:
    def __init__(self):
        self.signal_map     = None       # vbRcSignals sheet
        self.kpi_spec       = None       # KPI sheet
        self.graph_spec     = None       # graphSpec sheet
        self.line_colors    = None       # lineColors sheet
        self.marker_shapes  = None       # markerShapes sheet
        self.calibratables  = {}         # calibratables 

    @classmethod
    def from_json(cls, json_config_path):
        """Create Config object from JSON file."""
        cfg = cls()

        config_struct = cls._load_config(json_config_path)

        # --- SignalMap & KPI & PlotSpec (all in one Excel) ---
        spec_cfg   = config_struct["SignalMap_KPI_PlotSpec"]
        spec_path  = spec_cfg["FilePath"]
        sheet_list = spec_cfg["Sheets"]

        signal_kpi_plot_spec = cls._load_signal_map_kpi_plot_spec(spec_path, sheet_list)

        # Normalize keys for safe access
        sheet_map = {k.lower(): v for k, v in signal_kpi_plot_spec.items()}

        # Assign sheets
        cfg.signal_map      = sheet_map.get("vbrcsignals")
        cfg.graph_spec      = sheet_map.get("graphspec")
        cfg.line_colors     = sheet_map.get("linecolors")
        cfg.marker_shapes   = sheet_map.get("markershapes")
        cfg.kpi_spec        = sheet_map.get("kpi")

        # ✅ normalize signal_map column headers
        if cfg.signal_map is not None:
            cfg.signal_map.columns = cfg.signal_map.columns.str.strip().str.lower()

        # --- Calibration ---
        calib_cfg           = config_struct["Calibration"]
        calib_file          = calib_cfg["FilePath"]
        sheet_defs          = calib_cfg["Sheets"]
        cfg.calibratables   = cls._load_calibratables(calib_file, sheet_defs)

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

        if "SignalMap_KPI_PlotSpec" not in params or "FilePath" not in params["SignalMap_KPI_PlotSpec"]:
            raise ValueError("Missing SignalMap_KPI_PlotSpec.FilePath in config.")
        if "Sheets" not in params["SignalMap_KPI_PlotSpec"]:
            raise ValueError("SignalMap_KPI_PlotSpec.Sheets must be defined in config.")

        if "Calibration" not in params or "FilePath" not in params["Calibration"]:
            raise ValueError("Missing Calibration.FilePath in config.")
        if "Sheets" not in params["Calibration"]:
            raise ValueError("Calibration.Sheets must be defined in config.")

        return params

    @staticmethod
    def _load_signal_map_kpi_plot_spec(file_path, sheet_list):
        """Load vbRcSignals, graphSpec, lineColors, markerShapes, KPI from Excel."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"SignalMap_KPI_PlotSpec file not found: {file_path}")

        result = {}
        for sheet_name in sheet_list:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # ✅ normalize column headers
                df.columns = df.columns.str.strip().str.lower()
                result[sheet_name] = df
            except Exception as e:
                warnings.warn(f'Failed to read sheet "{sheet_name}": {e}')
        return result

    @staticmethod
    def _load_calibratables(calib_file, sheet_map):
        """
        Load calibration ranges from Excel using openpyxl directly (like MATLAB's readtable with Range).
        - If range is 2×N → stored as {"x": [...], "y": [...]}
        - If 1 row or >2 rows → stored as DataFrame
        - If truly empty → stored as None
        """
        file_path = Path(calib_file)
        if not file_path.exists():
            raise FileNotFoundError(f"Calibration file not found: {file_path}")

        wb = load_workbook(file_path, data_only=True)  # open once
        calibratables = {}

        for sheet, cal_defs in sheet_map.items():
            sheet_result = {}
            if sheet not in wb.sheetnames:
                warnings.warn(f'Sheet "{sheet}" not found in calibration file.')
                calibratables[sheet] = {}
                continue

            ws = wb[sheet]

            for cal_name, rng in cal_defs.items():
                try:
                    # Grab the cell range (e.g. "M7:X8")
                    cells = ws[rng]

                    # Convert to DataFrame
                    data = [[cell.value for cell in row] for row in cells]
                    df = pd.DataFrame(data)

                    # Reset index (keep all values)
                    df = df.reset_index(drop=True)

                    # ✅ If all values None, mark as empty
                    if df.isna().all().all():
                        print("[DEBUG] All values are None → treat as empty")
                        sheet_result[cal_name] = None
                    else:
                        # ✅ If exactly 2 rows, interpret as lookup table
                        if df.shape[0] == 2:
                            x = [v if v is not None else float("nan") for v in df.iloc[0].tolist()]
                            y = [v if v is not None else float("nan") for v in df.iloc[1].tolist()]
                            sheet_result[cal_name] = {"x": x, "y": y}
                        else:
                            # Store as DataFrame (e.g., thresholds with 1 row or multi-row tables)
                            sheet_result[cal_name] = df

                except Exception as e:
                    warnings.warn(
                        f'Failed to load "{cal_name}" from sheet "{sheet}" range "{rng}": {e}'
                    )
                    sheet_result[cal_name] = None

            calibratables[sheet] = sheet_result

        wb.close()
        return calibratables




    
