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
    PRE_TIME          = 6.0    # seconds before event
    POST_TIME         = 3.0    # seconds after event
    START_DECEL_DELTA = -30.0  # threshold for large negative change (AEB start)
    END_DECEL_DELTA   = 29.0   # threshold for positive change (AEB end)
    PB_TGT_DECEL      = -6.0   # threshold for AEB active state

    def __init__(self, input_handler, config=None):
        if input_handler is None or not hasattr(input_handler, "path_to_raw_data"):
            raise TypeError("EventDetector requires an InputHandler instance.")

        self.path_to_mdf = input_handler.path_to_raw_data
        self.path_to_mdf_chunks = os.path.join(self.path_to_mdf, "PostProcessing")

        if not os.path.exists(self.path_to_mdf_chunks):
            os.makedirs(self.path_to_mdf_chunks)

        # --- Load parameters from config if available ---
        if config is not None and hasattr(config, "params"):
            try:
                params = config.params or {}

                self.pre_time          = float(params.get("PRE_TIME", self.PRE_TIME))
                self.post_time         = float(params.get("POST_TIME", self.POST_TIME))
                self.start_decel_delta = float(params.get("START_DECEL_DELTA", self.START_DECEL_DELTA))
                self.end_decel_delta   = float(params.get("END_DECEL_DELTA", self.END_DECEL_DELTA))
                self.pb_tgt_decel      = float(params.get("PB_TGT_DECEL", self.PB_TGT_DECEL))

                print(
                    f"⏱ Using PRE={self.pre_time}s, POST={self.post_time}s, "
                    f"Δstart={self.start_decel_delta}, Δend={self.end_decel_delta} from config."
                )

            except Exception as e:
                warnings.warn(f"⚠️ Failed to load timing/delta params from config: {e}")
                self._apply_defaults()
        else:
            self._apply_defaults()

    def _apply_defaults(self):
        """Fallback to class defaults."""
        self.pre_time           = self.PRE_TIME
        self.post_time          = self.POST_TIME
        self.start_decel_delta  = self.START_DECEL_DELTA
        self.end_decel_delta    = self.END_DECEL_DELTA
        self.pb_tgt_decel       = self.PB_TGT_DECEL
        print(
            f"⚙️ Using default parameters: PRE={self.pre_time}s, POST={self.post_time}s, "
            f"Δstart={self.start_decel_delta}, Δend={self.end_decel_delta}"
        )

    # -------------------- Public API -------------------- #

    def process_all_files(self, pre_time: float = None, post_time: float = None):
        if pre_time is not None:
            self.pre_time  = float(pre_time)
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
            name, _   = os.path.splitext(fname)

            try:
                print(f"🔍 Reading MF4 file: {fname}")
                mdf = MDF(file_path)

                if "aebTargetDecel" not in mdf.channels_db.keys():
                    print(f"⚠️ File {fname} missing required signal 'aebTargetDecel' → skipped")
                    continue

                sig = mdf.get("aebTargetDecel")
                df  = pd.DataFrame({"time": sig.timestamps, "aebTargetDecel": sig.samples})

                start_times, end_times = self.detect_events(df)
                print(f"   ➝ Detected {len(start_times)} events")

                self.extract_aeb_events(mdf, start_times, end_times, name)

                del mdf, df, sig
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error processing {fname}: {e}")

    # -------------------- Event Detection -------------------- #

    def detect_events(self, df: pd.DataFrame):
        """Detect start and end times of AEB events."""
        time             = df["time"].values
        aeb_target_decel = df["aebTargetDecel"].values
        decel_delta      = np.diff(aeb_target_decel)

        # Start events
        locate_start     = np.where(np.diff(decel_delta < self.start_decel_delta))[0]
        start_mask       = aeb_target_decel[locate_start + 1] <= self.pb_tgt_decel
        start_times      = time[locate_start][start_mask]

        # End events
        locate_end = np.where(decel_delta > self.end_decel_delta)[0]
        end_times  = time[locate_end]

        if len(end_times) == 0 and len(start_times) > 0:
            buffer_time = max(1.0, self.post_time + 4)
            end_times   = start_times + buffer_time

        return start_times, end_times


    # -------------------- Event Extraction -------------------- #

    def extract_aeb_events(self, mdf: MDF, start_times, end_times, name: str):
        """Extract AEB event chunks and save into PostProcessing folder (MF4 only)."""

        if len(start_times) == 0:
            print(f"⚠️ No events detected for {name}")
            return

        # --- Reference time range of this MF4 file ---
        sig = mdf.get("aebTargetDecel")
        t_min, t_max = float(sig.timestamps[0]), float(sig.timestamps[-1])
        print(f"   🕒 File time range: {t_min:.3f}s → {t_max:.3f}s")

        for j, start_time in enumerate(start_times):
            # Clamp to valid window
            start_sec = max(start_time - self.pre_time, t_min)
            stop_sec  = (
                min(end_times[j] + self.post_time, t_max)
                if j < len(end_times)
                else min(start_time + self.post_time, t_max)
            )

            if stop_sec <= start_sec:
                print(f"⚠️ Skipping invalid window {start_sec:.3f}s → {stop_sec:.3f}s")
                continue

            print(f"   [DEBUG] cut window: {start_sec:.3f}s → {stop_sec:.3f}s")
            try:
                mdf_chunk = mdf.cut(start=start_sec, stop=stop_sec)
                if not mdf_chunk or len(mdf_chunk.channels_db) == 0:
                    print(f"⚠️ Empty chunk ({start_sec:.2f}s–{stop_sec:.2f}s) → no overlap.")
                    continue

                mf4_name = f"{name}_{j+1}.mf4"
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
