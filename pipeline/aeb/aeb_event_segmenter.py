import numpy as np
from pipeline.base.base_event_segmenter import BaseEventSegmenter
from utils.event_detector.aeb import detect_aeb_events


class AebEventSegmenter(BaseEventSegmenter):
    """Detects AEB events and extracts event chunks."""

    signal_name = "aebTargetDecel"

    PARAM_SPECS = {
        "start_decel_delta": {"default": -30.0, "type": float, "desc": "Δ start decel threshold"},
        "end_decel_delta":   {"default": 29.0,  "type": float, "desc": "Δ end decel threshold"},
        "pb_tgt_decel":      {"default": -6.0,  "type": float, "desc": "AEB PB target decel"},
    }

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
            aeb_target_decel=df[self.signal_name].values,
            start_decel_delta=self.start_decel_delta,
            end_decel_delta=self.end_decel_delta,
            pb_tgt_decel=self.pb_tgt_decel,
            post_time=self.post_time,
        )