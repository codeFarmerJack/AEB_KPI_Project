import numpy as np
from pipeline.base.base_event_segmenter import BaseEventSegmenter
from utils.event_detector.fcw import detect_fcw_events


class FcwEventSegmenter(BaseEventSegmenter):
    """Detects FCW events and extracts event chunks."""

    signal_name = "fcwRequest"

    def __init__(self, input_handler, config=None):
        super().__init__(
            input_handler,
            config=config,
            event_name="fcw",
            pre_key="PRE_TIME_FCW",
            post_key="POST_TIME_FCW",
        )

        # Backward compatibility alias
        self.path_to_fcw_chunks = self.path_to_chunks

    # -------------------- FCW-specific detection -------------------- #

    def detect_events(self, df, merge_window: float = 2.0):
        """Wrapper calling the shared detection function."""
        if "time" not in df or self.signal_name not in df:
            raise KeyError(f"DataFrame must contain 'time' and '{self.signal_name}' columns.")
        return detect_fcw_events(df["time"].values, df[self.signal_name].values, merge_window)