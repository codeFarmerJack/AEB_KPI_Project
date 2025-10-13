import numpy as np
from pipeline.base.base_event_segmenter import BaseEventSegmenter
from utils.event_detector.aeb import detect_aeb_events


class AebEventSegmenter(BaseEventSegmenter):
    """Detects AEB events and extracts event chunks."""

    signal_name = "aebTargetDecel"

    START_DECEL_DELTA = -30.0
    END_DECEL_DELTA   = 29.0
    PB_TGT_DECEL      = -6.0

    def __init__(self, input_handler, config=None):
        super().__init__(
            input_handler,
            config=config,
            event_name="aeb",
            pre_key="PRE_TIME_AEB",
            post_key="POST_TIME_AEB",
        )

        # Backward compatibility alias
        self.path_to_aeb_chunks = self.path_to_chunks

        if config is not None and hasattr(config, "params"):
            params = config.params or {}
            self.start_decel_delta = float(params.get("START_DECEL_DELTA", self.START_DECEL_DELTA))
            self.end_decel_delta   = float(params.get("END_DECEL_DELTA", self.END_DECEL_DELTA))
            self.pb_tgt_decel      = float(params.get("PB_TGT_DECEL", self.PB_TGT_DECEL))
        else:
            self.start_decel_delta = self.START_DECEL_DELTA
            self.end_decel_delta   = self.END_DECEL_DELTA
            self.pb_tgt_decel      = self.PB_TGT_DECEL

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