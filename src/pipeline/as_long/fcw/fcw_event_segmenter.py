from src.pipeline.base.base_event_segmenter import BaseEventSegmenter
from src.utils.event_detector.as_long.fcw import detect_fcw_events


class FcwEventSegmenter(BaseEventSegmenter):
    """Detects FCW events and extracts event chunks."""

    signal_name = "fcwRequest"

    def __init__(self, input_handler, config=None):
        super().__init__(
            input_handler,
            config=config,
            event_name="fcw",
        )

        # Backward compatibility alias
        self.in_path_fcw_chunks = self.out_path_chunks

    # -------------------- FCW-specific detection -------------------- #

    def detect_events(self, time, signal, merge_window: float = 2.0):
        """Wrapper calling the shared detection function."""
        return detect_fcw_events(time, signal, merge_window)
