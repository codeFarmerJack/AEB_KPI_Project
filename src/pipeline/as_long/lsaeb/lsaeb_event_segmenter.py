from src.pipeline.base.base_event_segmenter import BaseEventSegmenter
from src.utils.event_detector.as_long.lsaeb import detect_lsaeb_events


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
        self.in_path_lsaeb_chunks = self.out_path_chunks

    # -------------------- LSAEB-specific detection -------------------- #

    def detect_events(self, time, signal, merge_window: float = 2.0):
        """Ask the detector for times for chunk extraction."""
        return detect_lsaeb_events(
            time,
            signal,
            merge_window,
            output="times",
        )
