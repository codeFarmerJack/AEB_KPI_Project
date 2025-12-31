from src.pipeline.base.base_event_segmenter import BaseEventSegmenter
from src.utils.event_detector.as_long.aeb import detect_aeb_events


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
        self.in_path_aeb_chunks = self.out_path_chunks

    # -------------------- AEB-specific detection -------------------- #
    def detect_events(self, time, signal):
        """Wrapper calling the shared detection function."""
        return detect_aeb_events(
            time=time,
            aeb_request=signal,
            post_time=self.post_time,
        )
