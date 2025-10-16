import numpy as np
from pipeline.base.base_event_segmenter import BaseEventSegmenter
from utils.event_detector.aeb import detect_aeb_events


class AebEventSegmenter(BaseEventSegmenter):
    """Detects AEB events and extracts event chunks."""

    signal_name = "aebRequest"

    def __init__(self, input_handler, config=None):
        super().__init__(
            input_handler,
            config=config,
            event_name="aeb",
        )

        # Backward compatibility alias
        self.path_to_aeb_chunks = self.path_to_chunks

    # -------------------- AEB-specific detection -------------------- #
    def detect_events(self, df):
        """Wrapper calling the shared detection function."""
        if "time" not in df or self.signal_name not in df:
            raise KeyError(f"DataFrame must contain 'time' and '{self.signal_name}' columns.")

        return detect_aeb_events(
            time=df["time"].values,
            aeb_request=df[self.signal_name].values,
            post_time=self.post_time,
        )