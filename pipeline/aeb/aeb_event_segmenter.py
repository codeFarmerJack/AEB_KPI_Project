import numpy as np
from pipeline.base.base_event_segmenter import BaseEventSegmenter


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
        time = df["time"].values
        decel = df[self.signal_name].values
        delta = np.diff(decel)

        locate_start = np.where(np.diff(delta < self.start_decel_delta))[0]
        start_mask = decel[locate_start + 1] <= self.pb_tgt_decel
        start_times = time[locate_start][start_mask]

        locate_end = np.where(delta > self.end_decel_delta)[0]
        end_times = time[locate_end]

        if len(end_times) == 0 and len(start_times) > 0:
            buffer_time = max(1.0, self.post_time + 4)
            end_times = start_times + buffer_time

        return start_times, end_times
