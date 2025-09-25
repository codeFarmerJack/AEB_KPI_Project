import os
import numpy as np
from scipy.io import loadmat, savemat


class EventDetector:
    """
    EventDetector: detects AEB events in MAT files and extracts chunks.

    Each MAT file is expected to contain a variable 'signalMat',
    which is a dict-like structure with at least 'time' and 'aebTargetDecel'.
    """

    def __init__(self, input_handler, pre_time: float = 6.0, post_time: float = 3.0):
        """
        Args:
            input_handler: InputHandler instance (must have .pathToRawData)
            pre_time (float): seconds before event
            post_time (float): seconds after event
        """
        if input_handler is None or not hasattr(input_handler, "pathToRawData"):
            raise TypeError("EventDetector requires an InputHandler instance.")

        self.path_to_mat = input_handler.pathToRawData
        self.path_to_mat_chunks = os.path.join(self.path_to_mat, "PostProcessing")

        if not os.path.exists(self.path_to_mat_chunks):
            os.makedirs(self.path_to_mat_chunks)

        self.pre_time = float(pre_time)
        self.post_time = float(post_time)

    # -------------------- Public API -------------------- #

    def process_all_files(self):
        """Process all .mat files in path_to_mat."""
        mat_files = [f for f in os.listdir(self.path_to_mat) if f.endswith(".mat")]

        for fname in mat_files:
            file_path = os.path.join(self.path_to_mat, fname)
            name, _ = os.path.splitext(fname)

            try:
                mat_data = loadmat(file_path)
                if "signalMat" not in mat_data:
                    print(f"⚠️ {fname} missing 'signalMat' → skipped.")
                    continue

                signal_mat = mat_data["signalMat"]

                # Convert all fields into column vectors
                for key in signal_mat.dtype.names:
                    signal_mat[key][0, 0] = np.atleast_1d(signal_mat[key][0, 0]).flatten()

                self.process_single_file(signal_mat, name)

            except Exception as e:
                print(f"⚠️ Error processing {fname}: {e}")

    def process_single_file(self, signal_mat, name: str):
        """Detect events and extract AEB event chunks."""
        start_times, end_times = self.detect_events(signal_mat)
        self.extract_aeb_events(signal_mat, start_times, end_times, name)

    # -------------------- Event Detection -------------------- #

    def detect_events(self, signal_mat):
        """Detect start and end times of AEB events."""

        time = signal_mat["time"][0, 0].flatten()
        aeb_target_decel = signal_mat["aebTargetDecel"][0, 0].flatten()

        mode_change = np.diff(aeb_target_decel)

        # Start events: sharp decel drop
        locate_start = np.where(np.diff(mode_change < -30))[0]
        start_mask = aeb_target_decel[locate_start + 1] < -5.9
        start_times = time[locate_start][start_mask]

        # End events: decel recovery
        locate_end = np.where(mode_change > 20)[0]
        end_mask = aeb_target_decel[locate_end + 1] > 20
        end_times = time[locate_end][end_mask]

        # Fallback: if no end times, assume +7s after start
        if len(end_times) == 0 and len(start_times) > 0:
            end_times = start_times + 7

        return start_times, end_times

    # -------------------- Event Extraction -------------------- #

    def extract_aeb_events(self, signal_mat, start_times, end_times, name: str):
        """Extract event chunks and save into PostProcessing folder."""

        time = signal_mat["time"][0, 0].flatten()
        fields = signal_mat.dtype.names
        n_samples = len(time)

        for j, start_time in enumerate(start_times):
            # Start index
            start_sec = float(start_time - self.pre_time)
            start = self._find_time_index(time, start_sec)

            # End index (try to align with end_times[j])
            stop = 0
            if j < len(end_times):
                stop_sec = float(end_times[j] + self.post_time)
                stop = self._find_time_index(time, stop_sec)

            # Fallback if invalid stop
            if stop <= start or j >= len(end_times):
                stop_sec = float(start_time + self.post_time)
                stop = self._find_time_index(time, stop_sec)

            stop = min(stop, n_samples - 1)

            if stop > start:
                signal_chunk = {}
                for field in fields:
                    try:
                        values = signal_mat[field][0, 0].flatten()
                        signal_chunk[field] = values[start:stop + 1]
                    except Exception as e:
                        raise RuntimeError(f"Error slicing {field}: {e}")

                out_name = f"{name}_{j + 1}.mat"
                out_path = os.path.join(self.path_to_mat_chunks, out_name)

                try:
                    savemat(out_path, {"signalMatChunk": signal_chunk})
                    print(f"✅ Saved {out_path}")
                except Exception as e:
                    print(f"⚠️ Error saving {out_name}: {e}")

    # -------------------- Helpers -------------------- #

    @staticmethod
    def _find_time_index(time_array, target_sec):
        """Find nearest index in time_array to target_sec."""
        return int(np.argmin(np.abs(time_array - target_sec)))
