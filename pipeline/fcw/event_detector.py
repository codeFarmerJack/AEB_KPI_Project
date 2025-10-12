import os
import gc
import warnings
import numpy as np
import pandas as pd
from utils.signal_mdf import SignalMDF


class FcwEventDetector:
    """
    FcwEventDetector
    -------------
    Detects FCW events in MF4 files and extracts event chunks.

    Each MF4 file must contain a signal 'fcwRequest'.
    """

    # --- Fallback defaults (used only if not defined in config) ---
    PRE_TIME_FCW  = 6.0    # seconds before event
    POST_TIME_FCW = 3.0    # seconds after event

    def __init__(self, input_handler, config=None):
        if input_handler is None or not hasattr(input_handler, "path_to_raw_data"):
            raise TypeError("FcwEventDetector requires an InputHandler instance.")

        self.path_to_mdf = input_handler.path_to_raw_data
        self.path_to_fcw_chunks = os.path.join(self.path_to_mdf, "fcw_chunks")

        if not os.path.exists(self.path_to_fcw_chunks):
            os.makedirs(self.path_to_fcw_chunks)

        # --- Load parameters from config if available ---
        if config is not None and hasattr(config, "params"):
            try:
                params = config.params or {}

                self.pre_time  = float(params.get("PRE_TIME_FCW", self.PRE_TIME_FCW))
                self.post_time = float(params.get("POST_TIME_FCW", self.POST_TIME_FCW))

                print(
                    f"⏱ Using PRE={self.pre_time}s, POST={self.post_time}s from config."
                )

            except Exception as e:
                warnings.warn(f"⚠️ Failed to load timing/delta params from config: {e}")
                self._apply_defaults()
        else:
            self._apply_defaults()

    def _apply_defaults(self):
        """Fallback to class defaults."""
        self.pre_time  = self.PRE_TIME_FCW
        self.post_time = self.POST_TIME_FCW
        print(
            f"⚙️ Using default parameters: PRE={self.pre_time}s, POST={self.post_time}s from config."
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
                # ✅ Use SignalMDF instead of raw MDF
                mdf = SignalMDF(file_path)

                # ✅ Access via dot-notation
                if mdf.fcwRequest.size == 0:
                    print(f"⚠️ File {fname} missing required signal 'fcwRequest' → skipped")
                    continue        

                df = pd.DataFrame({
                    "time": mdf.time,
                    "fcwRequest": mdf.fcwRequest
                })

                start_times, end_times = self.detect_fcw_events(df)
                print(f"   ➝ Detected {len(start_times)} events")

                self.extract_fcw_events(mdf, start_times, end_times, name)

                del mdf, df
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error processing {fname}: {e}")

    # -------------------- Event Detection -------------------- #

    def detect_fcw_events(self, df: pd.DataFrame, merge_window: float = 2.0):
        """
        Detect FCW (Forward Collision Warning) events.
        
        Parameters
        ----------
        df : pd.DataFrame
            Must contain columns ['time', 'fcwRequest'].
        merge_window : float, optional
            If two events occur within this time window (seconds), merge them as one.
        
        Returns
        -------
        start_times : np.ndarray
            Start times of merged FCW events.
        end_times : np.ndarray
            End times of merged FCW events.
        """
        if "time" not in df or "fcwRequest" not in df:
            raise KeyError("Input DataFrame must contain 'time' and 'fcwRequest' columns.")

        time = df["time"].values
        fcw = df["fcwRequest"].values.astype(float)

        # --- Detect transitions ---
        fcw_prev = np.roll(fcw, 1)
        fcw_prev[0] = fcw[0]

        # Rising edge: 0 → 2 or 3
        start_indices = np.where((fcw_prev == 0) & ((fcw == 2) | (fcw == 3)))[0]
        # Falling edge: 2/3 → 0
        end_indices = np.where(((fcw_prev == 2) | (fcw_prev == 3)) & (fcw == 0))[0]

        start_times = time[start_indices]
        end_times   = time[end_indices]

        print(f"DEBUG: Raw starts = {start_times}")
        print(f"DEBUG: Raw ends   = {end_times}")

        # --- Handle unclosed events (if signal ends with FCW active) ---
        if len(start_times) > len(end_times):
            end_times = np.append(end_times, time[-1])

        # --- Merge nearby events ---
        merged_starts = []
        merged_ends = []
        if len(start_times) == 0:
            return np.array([]), np.array([])

        current_start = start_times[0]
        current_end = end_times[0]

        for i in range(1, len(start_times)):
            next_start = start_times[i]
            next_end   = end_times[i]

            # If next_start is close to previous end (< merge_window) → merge
            if next_start - current_end <= merge_window:
                current_end = next_end
            else:
                merged_starts.append(current_start)
                merged_ends.append(current_end)
                current_start = next_start
                current_end = next_end

        merged_starts.append(current_start)
        merged_ends.append(current_end)

        start_times = np.array(merged_starts)
        end_times = np.array(merged_ends)

        print(f"DEBUG: Merged FCW events:")
        for s, e in zip(start_times, end_times):
            print(f"  → Event from {s:.3f}s to {e:.3f}s (duration = {e-s:.2f}s)")

        return start_times, end_times


    # -------------------- Event Extraction -------------------- #

    def extract_fcw_events(self, mdf: "SignalMDF", start_times, end_times, name: str):
        """Extract FCW event chunks and save into mdf_chunks folder (MF4 only)."""

        if len(start_times) == 0:
            print(f"⚠️ No FCW events detected for {name}")
            return

        # --- Signal existence check ---
        if not hasattr(mdf, "fcwRequest"):
            print(f"⚠️ Missing 'fcwRequest' signal → cannot extract chunks.")
            return

        sig = mdf.fcwRequest
        if sig.size == 0:
            print(f"⚠️ Empty 'fcwRequest' samples → cannot extract chunks.")
            return

        # --- File time range ---
        t_min, t_max = float(mdf.time[0]), float(mdf.time[-1])
        print(f"   🕒 File time range: {t_min:.3f}s → {t_max:.3f}s")

        # --- Create FCW chunk path ---
        if not hasattr(self, "path_to_fcw_chunks"):
            self.path_to_fcw_chunks = os.path.join(self.path_to_mdf, "fcw_chunks")
            os.makedirs(self.path_to_fcw_chunks, exist_ok=True)

        # --- Loop over each FCW event ---
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

            print(f"   [DEBUG] Cutting FCW window: {start_sec:.3f}s → {stop_sec:.3f}s")

            try:
                # --- Extract segment ---
                mdf_chunk = mdf.cut(start=start_sec, stop=stop_sec)
                if not mdf_chunk or len(mdf_chunk.channels_db) == 0:
                    print(f"⚠️ Empty FCW chunk ({start_sec:.2f}s–{stop_sec:.2f}s) → no overlap.")
                    continue

                # --- Save MF4 chunk ---
                mf4_name = f"{name}_fcw_{j+1:02d}.mf4"
                mf4_path = os.path.join(self.path_to_fcw_chunks, mf4_name)
                mdf_chunk.save(mf4_path, overwrite=True)
                print(f"   ✅ Saved FCW event {j+1}: {start_sec:.2f}s → {stop_sec:.2f}s → {mf4_name}")

                # --- Clean up ---
                del mdf_chunk
                gc.collect()

            except Exception as e:
                print(f"⚠️ Error saving FCW event {j+1} of {name}: {e}")
