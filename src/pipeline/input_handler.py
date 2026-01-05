import os
import gc
from pathlib import Path
from typing import Optional, Union
from asammdf import MDF
from src.utils.path_manager import get_resource, init_tkinter_for_bundle
from src.utils.mf4_extractor import mf4_extractor
from src.utils.mf4_postprocess import build_signal, merge_signals, postprocess_signals
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

        self.signal_map = config.signal_map
        self.enum_mapper = EnumMapper(get_resource("config/enum_definitions.yaml"))

        # --- Load parameters from class and then override with config ---
        load_params_from_class(self)
        load_params_from_config(self, config)

        self.in_path_raw_data, self._provided_files = self._resolve_input(
            input_path,
            mf4_files,
        )

        out_path = Path(self.in_path_raw_data) / "extracted"
        out_path.mkdir(parents=True, exist_ok=True)
        self.out_path_extracted = str(out_path)

    # -------------------- Public API -------------------- #
    def process_mf4_files(self) -> None:
        """
        Process MF4 files:

        Workflow:
        1. Load and extract signals using mf4_extractor()
        2. Close the raw MF4 handle immediately after extraction
        3. Post-process signals (filters + unit conversions)
        4. Merge original + derived signals
        5. Map enum/categorical signals to integer values using enum_definitions.yaml
        6. Save all signals into a new MDF file
        named '<original>_extracted.mf4' inside the 'extracted' subfolder
        7. Close the new MDF file and force memory cleanup
        """

        mf4_paths = self._collect_mf4_paths()
        if self._provided_files is not None:
            print(f"🔎 Processing {len(mf4_paths)} selected MF4 file(s)...")
        else:
            print(f"🔎 Found {len(mf4_paths)} MF4 file(s) to process...")

        if not mf4_paths:
            print("⚠️ No MF4 files found.")
            return

        for full_path in mf4_paths:
            self._process_file(full_path)

    def _resolve_input(self, input_path, mf4_files):
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

            return str(normalized_input), [str(p) for p in normalized_files]

        if normalized_input:
            if not normalized_input.exists():
                raise ValueError(f"Provided MF4 folder does not exist: {normalized_input}")
            return str(normalized_input), None

        return self._prompt_for_input_folder(), None

    def _prompt_for_input_folder(self):
        print("📂 Please select the MF4 folder...")
        init_tkinter_for_bundle()

        root = tk.Tk()
        root.withdraw()
        folder = filedialog.askdirectory(title="Select MF4 Folder")
        if not folder:
            raise ValueError("No MF4 folder selected. Aborting.")

        folder = os.path.abspath(folder)
        print(f"✅ Selected MF4 folder: {folder}")
        return folder

    def _collect_mf4_paths(self):
        if self._provided_files is not None:
            return [Path(p) for p in self._provided_files]

        return [
            Path(self.in_path_raw_data) / f
            for f in os.listdir(self.in_path_raw_data)
            if f.lower().endswith(".mf4")
        ]

    def _process_file(self, full_path: Path):
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
                return

            # --- 2️⃣ Post-process signals (filters + conversions) ---
            derived = postprocess_signals(data, cutoff_freq=self.cutoff_freq)
            merged = merge_signals(data, derived)

            # --- 3️⃣ Save merged signals to new MDF ---
            new_mdf = MDF()
            signals = []
            for col, series in merged.items():
                try:
                    signals.append(build_signal(col, series, self.enum_mapper))
                except Exception as e:
                    print(f"⚠️ Failed to append signal {col}: {e}")
            if signals:
                new_mdf.append(signals)

            extracted_file = Path(self.out_path_extracted) / f"{full_path.stem}_extracted.mf4"

            # Save to the extracted folder
            new_mdf.save(str(extracted_file), overwrite=True)

            # 🔒 IMPORTANT: close the new MDF file too!
            try:
                new_mdf.close()
                print("   🔒 Closed new extracted MDF file.")
            finally:
                # ---------- CRITICAL CLEANUP ----------
                # remove references
                try:
                    del data, derived, merged, sigs, summary, used, raster, mods, new_mdf
                except Exception:
                    pass

                # Force garbage collection to free memory
                gc.collect()

            print(f"💾 Saved extracted + processed signals → {extracted_file}")

        except Exception as e:
            print(f"❌ Error processing {file}: {e}")
