import numpy as np
from pipeline.as_long.base.base_event_segmenter import BaseEventSegmenter
from utils.event_detector.as_long.lsaeb import detect_lsaeb_events


class LsaebEventSegmenter(BaseEventSegmenter):
    """Detects LSAEB (Low-Speed AEB) events and extracts event chunks."""

    signal_name = "cpmEventType"

    def __init__(self, input_handler, config=None):
        super().__init__(
            input_handler,
            config=config,
            event_name="lsaeb",
        )

        # Backward compatibility alias
        self.path_to_lsaeb_chunks = self.path_to_chunks

    # -------------------- LSAEB-specific detection -------------------- #

    def detect_events(self, df, merge_window: float = 2.0):
        """Wrapper calling the shared detection function."""
        if "time" not in df or self.signal_name not in df:
            raise KeyError(f"DataFrame must contain 'time' and '{self.signal_name}' columns.")
        return detect_lsaeb_events(df["time"].values, df[self.signal_name].values, merge_window)
