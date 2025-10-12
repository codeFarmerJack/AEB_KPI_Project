import os
import gc
import warnings
import numpy as np
import pandas as pd
from utils.signal_mdf import SignalMDF


class BaseEventDetector:
    """Base class for all event detectors (AEB, FCW, etc.)."""

    # --- Default pre/post timing (subclasses may override) ---
    PRE_TIME_DEFAULT  = 6.0
    POST_TIME_DEFAULT = 3.0

    def __init__(self, input_handler, config=None, event_name="base", pre_key=None, post_key=None):
        if input_handler is None or not hasattr(input_handler, "path_to_raw_data"):
            raise TypeError(f"{self.__class__.__name__} requires an InputHandler instance.")

        self.event_name = event_name.lower()
        self.path_to_mdf = input_handler.path_to_raw_data

        # --- Set folder for extracted chunks ---
        self.path_to_chunks = os.path.join(self.path_to_mdf, f"{self.event_name}_chunks")
        os.makedirs(self.path_to_chunks, exist_ok=True)

        # --- Load timing params from config ---
        self.pre_time = self.PRE_TIME_DEFAULT
        self.post_time = self.POST_TIME_DEFAULT
        if config is not None and hasattr(config, "params"):
            try:
                params = config.params or {}
                self.pre_time = float(params.get(pre_key, self.PRE_TIME_DEFAULT))
                self.post_time = float(params.get(post_key, self.POST_TIME_DEFAULT))
                print(f"⏱ {self.event_name.upper()}: Using PRE={self.pre_time}s, POST={self.post_time}s from config.")
            except Exception as e:
                warnings.warn(f"⚠️ Failed to load timing params for {self.event_name}: {e}")
        else:
            print(f"⚙️ Using default timing: PRE={self.pre_time}s, POST={self.post_time}s")

    # -------------------- Common file processing -------------------- #

    def process_all_files(self):
        """Loop over all *_extracted.mf4 files and detect/extract events."""
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
                mdf = SignalMDF(file_path)

                # Validate required signal
                if not hasattr(mdf, self.signal_name):
                    print(f"⚠️ File {fname} missing required signal '{self.signal_name}' → skipped")
                    continue

                sig = getattr(mdf, self.signal_name)
                if sig.size == 0:
                    print(f"⚠️ '{self.signal_name}' empty → skipped")
                    continue

                df = pd.DataFrame({"time": mdf.time, self.signal_name: sig})

                start_times, end_times = self.detect_events(df)
                print(f"   ➝ Detected {len(start_times)} {self.event_name.upper()} events")

                self.extract_events(mdf, start_times, end_times, name)

                del mdf, df
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error processing {fname}: {e}")

    # -------------------- Common event extraction -------------------- #

    def extract_events(self, mdf: "SignalMDF", start_times, end_times, name: str):
        """Extract event chunks and save them as MF4 files."""
        if len(start_times) == 0:
            print(f"⚠️ No {self.event_name.upper()} events detected for {name}")
            return

        t_min, t_max = float(mdf.time[0]), float(mdf.time[-1])
        print(f"   🕒 File time range: {t_min:.3f}s → {t_max:.3f}s")

        for j, start_time in enumerate(start_times):
            start_sec = max(start_time - self.pre_time, t_min)
            stop_sec = (
                min(end_times[j] + self.post_time, t_max)
                if j < len(end_times)
                else min(start_time + self.post_time, t_max)
            )

            if stop_sec <= start_sec:
                print(f"⚠️ Skipping invalid window {start_sec:.3f}s → {stop_sec:.3f}s")
                continue

            print(f"   [DEBUG] Cutting {self.event_name.upper()} window: {start_sec:.3f}s → {stop_sec:.3f}s")

            try:
                mdf_chunk = mdf.cut(start=start_sec, stop=stop_sec)
                if not mdf_chunk or len(mdf_chunk.channels_db) == 0:
                    print(f"⚠️ Empty chunk ({start_sec:.2f}s–{stop_sec:.2f}s) → no overlap.")
                    continue

                mf4_name = f"{name}_{self.event_name}_{j+1:02d}.mf4"
                mf4_path = os.path.join(self.path_to_chunks, mf4_name)
                mdf_chunk.save(mf4_path, overwrite=True)
                print(f"   ✅ Saved {self.event_name.upper()} event {j+1}: {start_sec:.2f}s → {stop_sec:.2f}s → {mf4_name}")

                del mdf_chunk
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error saving {self.event_name.upper()} event {j+1} of {name}: {e}")
