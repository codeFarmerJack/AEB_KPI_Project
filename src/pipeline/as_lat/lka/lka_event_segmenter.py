import numpy as np
from src.utils.event_detector.as_lat.lka import detect_lka_events
from src.pipeline.base.base_event_segmenter import BaseEventSegmenter

class LkaEventSegmenter(BaseEventSegmenter):
    """Detects LKA (Lane Keeping Assist) events and extracts event chunks."""

    signal_name = "lkaInterventionStatus"

    def __init__(self, input_handler, config=None):
        super().__init__(
            input_handler,
            config=config,
            event_name="lka",
        )

        # Override pre/post window times (default: 0.2s before start, 0.2 s after end)
        self.pre_time = 0.2
        self.post_time = 0.2

        # Optional backward compatibility alias
        self.in_path_lka_chunks = self.out_path_chunks

    # -------------------- LKA-specific detection -------------------- #

    def detect_events(self, df):
        """
        Detect start/end times of LKA events using lkaInterventionStatus signal.

        Parameters
        ----------
        df : pandas.DataFrame
            Must contain columns ['time', 'lkaInterventionStatus'].

        Returns
        -------
        start_times, end_times : np.ndarray
            Start and end times (seconds) of detected LKA events.
        """
        if "time" not in df or self.signal_name not in df:
            raise KeyError(f"DataFrame must contain 'time' and '{self.signal_name}' columns.")

        return detect_lka_events(
            df["time"].values,
            df[self.signal_name].values,
            output="times",
        )