import os
import warnings
import numpy as np
from typing import List
from asammdf import MDF, Signal
from utils.mf4_extractor import mf4_extractor
from utils.signal_filters import accel_filter
from utils.enum_loader import EnumMapper

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
    RESAMPLE_RATE = 0.01   # seconds (100 Hz)
    CUTOFF_FREQ   = 10.0   # Hz 

    def __init__(self, config):
        """
        Constructor: accepts a Config object, loads key parameters,
        and prompts the user to select the folder containing MF4 files.
        """

        # --- Validate config object ---
        if config is None:
            raise ValueError("Configuration object is required for initialization.")
        if not hasattr(config, "signal_map"):
            raise TypeError("Config object must define signal_map")

        # --- Assign base attributes ---
        self.signal_map = config.signal_map
        self.path_to_raw_data = None

        # --- Default fallback parameters ---
        self.resample_rate = self.RESAMPLE_RATE
        self.cutoff_freq   = self.CUTOFF_FREQ   # Hz (default for accel_filter)

        # --- Load parameters from config.params if available ---
        if hasattr(config, "params") and isinstance(config.params, dict):
            params = config.params or {}

            # RESAMPLE_RATE
            if "RESAMPLE_RATE" in params:
                try:
                    self.resample_rate = float(params["RESAMPLE_RATE"])
                    print(f"📈 Using RESAMPLE_RATE={self.resample_rate:.3f}s from config.")
                except Exception as e:
                    warnings.warn(f"⚠️ Invalid RESAMPLE_RATE in config: {e}")
            
            # CUTOFF_FREQ
            if "CUTOFF_FREQ" in params:
                try:
                    self.cutoff_freq = float(params["CUTOFF_FREQ"])
                    print(f"🎚 Using CUTOFF_FREQ={self.cutoff_freq:.1f} Hz from config.")
                except Exception as e:
                    warnings.warn(f"⚠️ Invalid CUTOFF_FREQ in config: {e}")

        else:
            print(f"⚙️ Using default RESAMPLE_RATE={self.resample_rate:.3f}s, "
                f"CUTOFF_FREQ={self.cutoff_freq:.1f} Hz")

        # --- Prompt user for MF4 folder ---
        print("📂 Please select the MF4 folder...")
        root = tk.Tk()
        root.withdraw()  # hide main window
        folder = filedialog.askdirectory(title="Select MF4 Folder")

        if not folder:
            raise ValueError("No MF4 folder selected. Aborting.")
        
        self.path_to_raw_data = os.path.abspath(folder)
        print(f"✅ Selected MF4 folder: {self.path_to_raw_data}")

    # -------------------- Public API -------------------- #
    def process_mf4_files(self) -> None:
        """
        Process MF4 files:
        1. Extract specified signals using mf4_extractor()
        2. Filter longActAccel & latActAccel
        3. Convert egoSpeed (m/s → km/h)
        4. Save all signals to '_extracted.mf4'
        """

        mf4_files = [f for f in os.listdir(self.path_to_raw_data) if f.lower().endswith(".mf4")]
        print(f"🔎 Found {len(mf4_files)} MF4 file(s) to process...")

        if not mf4_files:
            print("⚠️ No MF4 files found in the selected folder.")
            return

        for file in mf4_files:
            full_path = os.path.join(self.path_to_raw_data, file)
            print(f"\n📂 Processing file: {file}")

            try:
                # --- 1️⃣ Extract signals ---
                data, mdf_obj, sigs, summary, used, raster, mods = mf4_extractor(
                    dat_path=full_path,
                    signal_database=self.signal_map,
                    req=None,
                    resample=self.resample_rate,
                    convert_to_tact_unit=True,
                )

                if data.empty:
                    print(f"⚠️ Warning: no data extracted from {file}")
                    continue

                # --- 2️⃣ Filter long & lat acceleration ---
                for sig in ["longActAccel", "latActAccel"]:
                    if sig in data.columns:
                        try:
                            sig_flt = accel_filter(
                                data.index.values,
                                data[sig].values,
                                cutoff_freq=self.cutoff_freq
                            )
                            data[f"{sig}Flt"] = sig_flt
                            print(f"   ✅ Filtered signal: {sig} → {sig}Flt")
                        except Exception as e:
                            warnings.warn(f"⚠️ Failed to filter {sig}: {e}")
                    else:
                        warnings.warn(f"⚠️ Signal '{sig}' not found in extracted data.")
                # --- 3️⃣ Convert egoSpeed from m/s to km/h ---
                if "egoSpeed" in data.columns:
                    try:
                        data["egoSpeedKph"] = data["egoSpeed"] * 3.6
                        print("   ✅ Converted egoSpeed → egoSpeedKph (m/s → km/h)")
                    except Exception as e:
                        warnings.warn(f"⚠️ Failed to convert egoSpeed: {e}")
                else:
                    warnings.warn("⚠️ Signal 'egoSpeed' not found in extracted data.")

                # --- 4️⃣ Save both raw + filtered signals to new MDF ---

                mapper = EnumMapper("config/enum_definitions.yaml")
                
                new_mdf = MDF()
                for col in data.columns:
                    try:
                        series = data[col]
                        if series.dtype == object:
                            enum_name = mapper.get_enum_for_signal(col)

                            if enum_name:
                                # Use YAML enum mapping
                                enum_table = mapper.enums.get(enum_name, {})
                                encoded = series.astype(str).map(lambda v: enum_table.get(v, np.nan))
                                if encoded.isna().any():
                                    missing = series[encoded.isna()].unique().tolist()
                                    print(f"⚠️ Unmapped values in {col}: {missing}")
                                samples = encoded.fillna(-1).astype(np.int16).to_numpy()

                                sig = Signal(
                                    samples=samples,
                                    timestamps=data.index.values,
                                    name=col,
                                    unit="u[1]",
                                    comment=f"Enum mapping: {enum_name}"
                                )
                            else:
                                # fallback categorical encoding
                                categories, encoded = np.unique(series.astype(str), return_inverse=True)
                                sig = Signal(
                                    samples=encoded.astype(np.int16),
                                    timestamps=data.index.values,
                                    name=col,
                                    unit="u[1]",
                                    comment=f"Categorical mapping: {dict(enumerate(categories))}"
                                )

                        else:
                            sig = Signal(
                                samples=series.to_numpy(dtype=np.float64),
                                timestamps=data.index.values,
                                name=col,
                                unit="u[1]"
                            )

                        new_mdf.append(sig)

                    except Exception as e:
                        print(f"⚠️ Failed to append signal {col}: {e}")


                extracted_file = os.path.splitext(full_path)[0] + "_extracted.mf4"
                new_mdf.save(extracted_file, overwrite=True)
                print(f"💾 Saved extracted + filtered signals → {extracted_file}")

            except Exception as e:
                print(f"❌ Error processing {file}: {e}")
