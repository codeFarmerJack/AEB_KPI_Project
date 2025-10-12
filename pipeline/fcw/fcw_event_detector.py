import numpy as np
from pipeline.base.base_event_detector import BaseEventDetector


class FcwEventDetector(BaseEventDetector):
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
        time = df["time"].values
        fcw = df[self.signal_name].values.astype(float)

        fcw_prev = np.roll(fcw, 1)
        fcw_prev[0] = fcw[0]

        start_idx = np.where((fcw_prev == 0) & ((fcw == 2) | (fcw == 3)))[0]
        end_idx   = np.where(((fcw_prev == 2) | (fcw_prev == 3)) & (fcw == 0))[0]

        start_times = time[start_idx]
        end_times   = time[end_idx]

        if len(start_times) > len(end_times):
            end_times = np.append(end_times, time[-1])

        if len(start_times) == 0:
            return np.array([]), np.array([])

        merged_starts, merged_ends = [], []
        cur_s, cur_e = start_times[0], end_times[0]
        for i in range(1, len(start_times)):
            ns, ne = start_times[i], end_times[i]
            if ns - cur_e <= merge_window:
                cur_e = ne
            else:
                merged_starts.append(cur_s)
                merged_ends.append(cur_e)
                cur_s, cur_e = ns, ne
        merged_starts.append(cur_s)
        merged_ends.append(cur_e)

        return np.array(merged_starts), np.array(merged_ends)
