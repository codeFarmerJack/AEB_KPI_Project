import os
import sys
import gc
import warnings
from pathlib import Path
from typing import Optional, Union
import numpy as np
from asammdf import MDF, Signal
from src.utils.path_manager import get_resource, init_tkinter_for_bundle
from src.utils.mf4_extractor import mf4_extractor
from src.utils.signal_filters import accel_filter
from src.utils.enum_loader import EnumMapper
from src.utils.load_params import load_params_from_class, load_params_from_config

# For folder selection
import tkinter as tk
from tkinter import filedialog


class InputHandler:
    """
    InputHandler
    -------------
    Handles input configuration and processing of MF4 files.
    """

    PARAM_SPECS = {
        "resample_rate": {"default": 0.01, "type": float, "desc": "Resampling interval in seconds (e.g., 0.01 = 100 Hz)"},
        "cutoff_freq": {"default": 10.0, "type": float, "desc": "Low-pass filter cutoff frequency in Hz"},
    }

    def __init__(self, config, input_path: Optional[Union[str, Path]] = None, mf4_files=None):
        """
        Constructor: accepts a Config object, loads key parameters.
        If mf4_files/input_path are provided, uses them directly; otherwise,
        prompts the user to select the folder containing MF4 files.
        """

        # --- Validate config object ---
        if config is None:
            raise ValueError("Configuration object is required for initialization.")
        if not hasattr(config, "signal_map"):
            raise TypeError("Config object must define signal_map")

        # --- Assign base attributes ---
        self.signal_map         = config.signal_map
        self.in_path_raw_data   = None
        self.out_path_extracted = None
        self._provided_files    = None
        self.enum_mapper        = EnumMapper(get_resource("config/enum_definitions.yaml"))

        # --- Load parameters from class and then override with config ---
        load_params_from_class(self)
        if config:
            load_params_from_config(self, config)

        # --- Resolve input path / file list ---
        normalized_input = Path(input_path).expanduser().resolve() if input_path else None

        if mf4_files:
            normalized_files = [Path(p).expanduser().resolve() for p in mf4_files]
            missing = [str(p) for p in normalized_files if not p.exists()]
            if missing:
                raise ValueError(f"MF4 file(s) not found: {', '.join(missing)}")

            parent_dirs = {p.parent for p in normalized_files}
            if normalized_input:
                if any(parent != normalized_input for parent in parent_dirs):
                    raise ValueError("All MF4 files must reside in the provided input folder.")
            else:
                if len(parent_dirs) > 1:
                    raise ValueError("All provided MF4 files must be in the same folder.")
                normalized_input = parent_dirs.pop()

            self._provided_files = [str(p) for p in normalized_files]
            self.in_path_raw_data = str(normalized_input)

        elif normalized_input:
            if not normalized_input.exists():
                raise ValueError(f"Provided MF4 folder does not exist: {normalized_input}")
            self.in_path_raw_data = str(normalized_input)

        else:
            # --- Prompt user for MF4 folder ---
            print("📂 Please select the MF4 folder...")

            # Ensure Tcl/Tk works inside PyInstaller
            init_tkinter_for_bundle()

            # Always show folder selection dialog
            root = tk.Tk()
            root.withdraw()
            folder = filedialog.askdirectory(title="Select MF4 Folder")

            if not folder:
                raise ValueError("No MF4 folder selected. Aborting.")

            self.in_path_raw_data = os.path.abspath(folder)
            print(f"✅ Selected MF4 folder: {self.in_path_raw_data}")


        # --- Create subfolder for extracted files ---
        self.out_path_extracted = os.path.join(self.in_path_raw_data, "extracted")
        os.makedirs(self.out_path_extracted, exist_ok=True)

        # -------------------- Helper: Unit Conversions -------------------- #
    def _apply_conversions(self, data):
        """
        Apply all unit conversions to extracted MF4 signals.
        Adds new converted columns without overwriting originals.
        """

        CONVERSIONS = {
            "egoSpeed":            ("egoSpeedKph", lambda x: x * 3.6,    "m/s → km/h"),
            "steerWheelAngle":     ("steerWheelAngleDeg", np.degrees,    "rad → deg"),
            "steerWheelAngleSpeed":("steerWheelAngleSpeedDeg", np.degrees, "rad/s → deg/s"),
            "yawRate":             ("yawRateDeg", np.degrees,            "rad/s → deg/s"),
        }

        for src, (dst, func, desc) in CONVERSIONS.items():
            if src not in data.columns:
                warnings.warn(f"⚠️ Signal '{src}' not found in extracted data.")
                continue

            try:
                data[dst] = func(data[src])
                print(f"   ✅ Converted {src} → {dst} ({desc})")
            except Exception as e:
                warnings.warn(f"⚠️ Failed to convert {src}: {e}")

        return data


    # -------------------- Public API -------------------- #
    def process_mf4_files(self) -> None:
        """
        Process MF4 files:

        Workflow:
        1. Load and extract signals using mf4_extractor()
        2. Close the raw MF4 handle immediately after extraction
        3. Apply signal filtering:
            - longActAccel  → longActAccelFlt
            - latActAccel   → latActAccelFlt
        4. Apply unit conversions:
            - egoSpeed               (m/s → km/h)
            - steerWheelAngle        (rad → deg)
            - steerWheelAngleSpeed   (rad/s → deg/s)
            - yawRate                (rad/s → deg/s)
        5. Map enum/categorical signals to integer values using enum_definitions.yaml
        6. Save all signals (original + filtered + converted) into a new MDF file
        named '<original>_extracted.mf4' inside the 'extracted' subfolder
        7. Close the new MDF file and force memory cleanup
        """

        if self._provided_files is not None:
            mf4_paths = [Path(p) for p in self._provided_files]
            print(f"🔎 Processing {len(mf4_paths)} selected MF4 file(s)...")
        else:
            mf4_paths = [
                Path(self.in_path_raw_data) / f
                for f in os.listdir(self.in_path_raw_data)
                if f.lower().endswith(".mf4")
            ]
            print(f"🔎 Found {len(mf4_paths)} MF4 file(s) to process...")

        if not mf4_paths:
            print("⚠️ No MF4 files found.")
            return

        for full_path in mf4_paths:
            full_path = Path(full_path)
            file = full_path.name
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

                # --- right after extraction, immediately close raw MF4 ---
                try:
                    if hasattr(mdf_obj, "close"):
                        mdf_obj.close()
                        print("   🔒 Closed raw MF4 file handle.")
                except Exception as e:
                    print(f"⚠️ Failed to close mdf_obj: {e}")

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
                # --- 3️⃣ Apply unit conversions (throttle, steering, egoSpeed, yaw, etc.) ---
                data = self._apply_conversions(data)


                # --- 4️⃣ Save both raw + filtered signals to new MDF ---

                new_mdf = MDF()
                for col in data.columns:
                    try:
                        series = data[col]
                        if series.dtype == object:
                            enum_name = self.enum_mapper.get_enum_for_signal(col)

                            if enum_name:
                                # Use YAML enum mapping
                                enum_table = self.enum_mapper.enums.get(enum_name, {})
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

                # Extract just the base filename, e.g., "test.mf4" → "test_extracted.mf4"
                base_name = os.path.splitext(os.path.basename(full_path))[0] + "_extracted.mf4"

                # Build the new path inside the extracted folder
                extracted_file = os.path.join(self.out_path_extracted, base_name)

                # Save to the extracted folder
                new_mdf.save(extracted_file, overwrite=True)

                # 🔒 IMPORTANT: close the new MDF file too!
                try:
                    new_mdf.close()
                    print("   🔒 Closed new extracted MDF file.")
                finally:
                    # ---------- CRITICAL CLEANUP ----------
                    # remove references
                    try:
                        del data, sigs, summary, used, raster, mods, new_mdf
                    except Exception:
                        pass
                    
                    # Force garbage collection to free memory
                    gc.collect()
                
                print(f"💾 Saved extracted + filtered signals → {extracted_file}")

            except Exception as e:
                print(f"❌ Error processing {file}: {e}")
