import os
import pandas as pd
from typing import List, Optional
from utils.mdf_to_mat import mdf_to_mat


class InputHandler:
    """
    InputHandler: Handles input configuration and processing of MF4 files
    """

    def __init__(self, config):
        """
        Constructor: accepts a Config object and sets pathToRawData
        """
        if config is None:
            raise ValueError("Configuration object is required for initialization.")

        # Validate config type
        if not hasattr(config, "jsonConfigPath"):
            raise TypeError("Config object must define jsonConfigPath and related attributes.")

        # Mirror config properties
        self.jsonConfigPath = config.jsonConfigPath
        self.graphSpec = config.graphSpec
        self.lineColors = config.lineColors
        self.signalMap = config.signalMap
        self.signalPlotSpecPath = config.signalPlotSpecPath
        self.signalPlotSpecName = config.signalPlotSpecName

        # Ask for rawdata folder or take from config
        if hasattr(config, "pathToRawData") and config.pathToRawData:
            self.pathToRawData = os.path.abspath(config.pathToRawData)
        else:
            raise ValueError("Config must define pathToRawData with MF4 files.")

        if not os.path.isdir(self.pathToRawData):
            raise FileNotFoundError(f"Raw data folder not found: {self.pathToRawData}")

        # Verify MF4 presence
        mf4_files = [f for f in os.listdir(self.pathToRawData) if f.lower().endswith(".mf4")]
        if not mf4_files:
            raise FileNotFoundError(f"No MF4 files found in {self.pathToRawData}")

    def process_mf4_files(self, resample_rate: float = 0.01) -> List[dict]:
        """
        Process MF4 files: extract specified signals, save to MAT, and return processed data.

        Args:
            resample_rate (float): Resampling interval in seconds (default 0.01 = 100Hz)

        Returns:
            List[dict]: List of processed signal dictionaries (signalMat style)
        """
        mf4_files = [f for f in os.listdir(self.pathToRawData) if f.lower().endswith(".mf4")]
        processed_data = []

        print(f"    Found {len(mf4_files)} MF4 file(s) to process...")

        for file in mf4_files:
            full_path = os.path.join(self.pathToRawData, file)
            name, _ = os.path.splitext(file)
            try:
                # Process MF4 file with Python mdf_to_mat
                data, m, sigs, summary, used, raster, mods = mdf_to_mat(
                    dat_path=full_path,
                    signal_database=self.signalMap,
                    req=None,
                    resample=resample_rate,
                    convert_to_tact_unit=True
                )

                mat_file = os.path.join(self.pathToRawData, f"{name}.mat")

                if not data.empty:
                    # Build struct-like dict
                    signalMat = {"time": data.index.values.reshape(-1, 1)}
                    for col in data.columns:
                        valid_name = col.replace(".", "_").replace("-", "_").replace(" ", "_")
                        signalMat[valid_name] = data[col].values.reshape(-1, 1)

                    from scipy.io import savemat
                    savemat(mat_file, {"signalMat": signalMat})
                    print(f"    Processed: {file}, saved to {mat_file}")
                    processed_data.append(signalMat)
                else:
                    print(f"    Warning: no data extracted from {file}")
                    processed_data.append({})

            except Exception as e:
                print(f"Error processing {file}: {e}")
                processed_data.append({})

        return processed_data
