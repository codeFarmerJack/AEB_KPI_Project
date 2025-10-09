import os
import numpy as np
import pandas as pd
from asammdf import MDF
import gc
import warnings


class EventDetector:
    """
    EventDetector
    -------------
    Detects AEB events in MF4 files and extracts event chunks.

    Each MF4 file must contain a signal 'aebTargetDecel'.
    """

    # --- Fallback defaults (used only if not defined in config) ---
    PRE_TIME  = 6.0   # seconds before event
    POST_TIME = 3.0   # seconds after event

    def __init__(self, input_handler, config=None):
        if input_handler is None or not hasattr(input_handler, "path_to_raw_data"):
            raise TypeError("EventDetector requires an InputHandler instance.")

        self.path_to_mdf = input_handler.path_to_raw_data
        self.path_to_mdf_chunks = os.path.join(self.path_to_mdf, "PostProcessing")

        if not os.path.exists(self.path_to_mdf_chunks):
            os.makedirs(self.path_to_mdf_chunks)

        # --- Load timing parameters from config if available ---
        if config is not None and hasattr(config, "params"):
            try:
                params = config.params or {}
                self.pre_time = float(params.get("PRE_TIME", self.PRE_TIME))
                self.post_time = float(params.get("POST_TIME", self.POST_TIME))
                print(f"⏱ Using PRE_TIME={self.pre_time}s, POST_TIME={self.post_time}s from config.")
            except Exception as e:
                warnings.warn(f"⚠️ Failed to load PRE/POST_TIME from config: {e}")
                self.pre_time = self.PRE_TIME
                self.post_time = self.POST_TIME
        else:
            # Fall back to class defaults
            self.pre_time = self.PRE_TIME
            self.post_time = self.POST_TIME
            print(f"⚙️ Using default PRE_TIME={self.pre_time}s, POST_TIME={self.post_time}s")
    # -------------------- Public API -------------------- #

    def process_all_files(self, pre_time: float = None, post_time: float = None):
        if pre_time is not None:
            self.pre_time = float(pre_time)
        if post_time is not None:
            self.post_time = float(post_time)

        # Only process *_extracted.mf4 files
        mdf_files = [f for f in os.listdir(self.path_to_mdf) if f.endswith("_extracted.mf4")]
        print(f"\n📂 Found {len(mdf_files)} extracted MF4 files in {self.path_to_mdf}\n")

        if not mdf_files:
            print("⚠️ No extracted MF4 files found. Did you run InputHandler.process_mf4_files first?")
            return

        for fname in mdf_files:
            file_path = os.path.join(self.path_to_mdf, fname)
            name, _ = os.path.splitext(fname)

            try:
                print(f"🔍 Reading MF4 file: {fname}")
                mdf = MDF(file_path)

                # --- SAFELY check for required signal ---
                if "aebTargetDecel" not in mdf.channels_db.keys():
                    print(f"⚠️ File {fname} missing required signal 'aebTargetDecel' → skipped")
                    continue

                # --- Extract signal safely ---
                sig = mdf.get("aebTargetDecel")
                df = pd.DataFrame({
                    "time": sig.timestamps,
                    "aebTargetDecel": sig.samples
                })

                # --- Detect events ---
                start_times, end_times = self.detect_events(df)
                print(f"   ➝ Detected {len(start_times)} events")

                # --- Extract event chunks ---
                self.extract_aeb_events(mdf, start_times, end_times, name)

                # Cleanup memory
                del mdf, df, sig
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error processing {fname}: {e}")

    # -------------------- Event Detection -------------------- #

    def detect_events(self, df: pd.DataFrame):
        """Detect start and end times of AEB events."""
        time = df["time"].values
        aeb_target_decel = df["aebTargetDecel"].values

        mode_change = np.diff(aeb_target_decel)

        # Start events
        locate_start = np.where(np.diff(mode_change < -30))[0]
        start_mask = aeb_target_decel[locate_start + 1] < -5.9
        start_times = time[locate_start][start_mask]

        # End events
        locate_end = np.where(mode_change > 20)[0]
        end_mask = aeb_target_decel[locate_end + 1] > 20
        end_times = time[locate_end][end_mask]

        # Fallback if no end times
        if len(end_times) == 0 and len(start_times) > 0:
            buffer_time = max(1.0, self.post_time + 4)
            end_times = start_times + buffer_time

        return start_times, end_times

    # -------------------- Event Extraction -------------------- #

    def extract_aeb_events(self, mdf: MDF, start_times, end_times, name: str):
        """Extract event chunks and save into PostProcessing folder (MF4 only)."""
        for j, start_time in enumerate(start_times):
            start_sec = float(start_time - self.pre_time)

            if j < len(end_times):
                stop_sec = float(end_times[j] + self.post_time)
            else:
                stop_sec = float(start_time + self.post_time)

            try:
                mdf_chunk = mdf.cut(start=start_sec, stop=stop_sec)

                mf4_name = f"{name}_{j + 1}.mf4"
                mf4_path = os.path.join(self.path_to_mdf_chunks, mf4_name)

                mdf_chunk.save(mf4_path, overwrite=True)
                print(f"   ✅ Saved event {j+1}: {start_sec:.2f}s → {stop_sec:.2f}s → {mf4_name}")

                del mdf_chunk
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error saving event {j+1} of {name}: {e}")

    # -------------------- Helpers -------------------- #

    @staticmethod
    def _find_time_index(time_array, target_sec):
        """Find nearest index in time_array to target_sec."""
        return int(np.argmin(np.abs(time_array - target_sec)))
