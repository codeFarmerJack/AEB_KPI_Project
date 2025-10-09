import os
import warnings
from typing import List
from utils.mf4_extractor import mf4_extractor

# For folder selection
import tkinter as tk
from tkinter import filedialog


class InputHandler:
    """
    InputHandler
    -------------
    Handles input configuration and processing of MF4 files.

    Loads RESAMPLE_RATE from config (if available),
    and processes all MF4 files in the selected folder.
    """

    # --- Fallback default (used only if not defined in config) ---
    RESAMPLE_RATE = 0.01  # seconds (100 Hz)

    def __init__(self, config):
        """
        Constructor: accepts a Config object, keeps signal_map,
        and prompts the user to select MF4 folder.
        """
        if config is None:
            raise ValueError("Configuration object is required for initialization.")

        if not hasattr(config, "signal_map"):
            raise TypeError("Config object must define signal_map")

        self.signal_map = config.signal_map

        # --- Load resample rate from config if available ---
        if config is not None and hasattr(config, "params"):
            try:
                params = config.params or {}
                self.resample_rate = float(params.get("RESAMPLE_RATE", self.RESAMPLE_RATE))
                print(f"📈 Using RESAMPLE_RATE={self.resample_rate:.3f}s from config.")
            except Exception as e:
                warnings.warn(f"⚠️ Failed to load RESAMPLE_RATE from config: {e}")
                self.resample_rate = self.RESAMPLE_RATE
        else:
            self.resample_rate = self.RESAMPLE_RATE
            print(f"⚙️ Using default RESAMPLE_RATE={self.resample_rate:.3f}s")

        # --- Prompt user for MF4 folder ---
        print("📂 Please select the MF4 folder...")
        root = tk.Tk()
        root.withdraw()  # hide main window
        folder = filedialog.askdirectory(title="Select MF4 Folder")
        if not folder:
            raise ValueError("No MF4 folder selected. Aborting.")
        self.path_to_raw_data = os.path.abspath(folder)

    # -------------------- Public API -------------------- #
    def process_mf4_files(self) -> None:
        """
        Process MF4 files: extract specified signals,
        save to new MF4 + spec file (via mf4_extractor).
        """
        mf4_files = [f for f in os.listdir(self.path_to_raw_data) if f.lower().endswith(".mf4")]
        print(f"    Found {len(mf4_files)} MF4 file(s) to process...")

        for file in mf4_files:
            full_path = os.path.join(self.path_to_raw_data, file)
            print(f"    > Processing file: {full_path}")

            try:
                data, m, sigs, summary, used, raster, mods = mf4_extractor(
                    dat_path=full_path,
                    signal_database=self.signal_map,
                    req=None,
                    resample=self.resample_rate,
                    convert_to_tact_unit=True,
                )

                if data.empty:
                    print(f"    ⚠️ Warning: no data extracted from {file}")

            except Exception as e:
                print(f"❌ Error processing {file}: {e}")
