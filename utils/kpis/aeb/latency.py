import numpy as np
import pandas as pd
import warnings
from utils.event_detector.decel import detect_decel_onset


class AebLatencyCalculator:
    """
    Calculates AEB system latencies, including:
      1. Vehicle response latency (jerk / decel onset)
      2. Communication latency (PB→FB transition)

    Constructed directly from an AebKpiExtractor instance:
        self.latency_calc = AebLatencyCalculator(self)
    """

    # ------------------------------------------------------------------
    def __init__(self, extractor):
        """
        Initialize using parameters from the parent AebKpiExtractor instance.
        """
        self.neg_thd                = extractor.aeb_jerk_neg_thd
        self.latency_window_samples = extractor.latency_window_samples
        self.pb_tgt_decel           = extractor.pb_tgt_decel
        self.fb_tgt_decel           = extractor.fb_tgt_decel
        self.pb_duration            = extractor.pb_duration

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_all(self, mdf, kpi_table, row_idx, aeb_start_idx):
        """
        Compute both vehicle and communication latencies and
        update KPI table in place.
        """
        veh_latency = self._compute_vehicle_latency(mdf, row_idx, aeb_start_idx)
        comm_latency = self._compute_communication_latency(mdf, row_idx)

        # Write directly into KPI table
        kpi_table.at[row_idx, "aebSysRespTime"] = veh_latency["resp_time"]
        kpi_table.at[row_idx, "aebDeadTime"] = veh_latency["dead_time"]
        kpi_table.at[row_idx, "commLatency"] = comm_latency["comm_latency"]

    # ------------------------------------------------------------------
    # Vehicle latency (jerk-based)
    # ------------------------------------------------------------------
    def _compute_vehicle_latency(self, mdf, row_idx, aeb_start_idx):
        time = np.asarray(mdf.time)
        accel = np.asarray(mdf.longActAccelFlt)

        start_idx = aeb_start_idx
        end_idx = min(start_idx + self.latency_window_samples, len(time) - 1)
        if start_idx >= end_idx:
            warnings.warn(f"[Row {row_idx}] Invalid range for vehicle latency; set to 0.")
            return {"resp_time": 0.0, "dead_time": 0.0}

        # Compute jerk and detect onset
        jerk = np.gradient(accel[start_idx:end_idx + 1], time[start_idx:end_idx + 1])
        resp_idx_rel = detect_decel_onset(jerk, self.neg_thd)

        if resp_idx_rel is not None:
            resp_idx_abs = start_idx + resp_idx_rel
            t_sys_resp = time[resp_idx_abs]
        else:
            warnings.warn(f"[Row {row_idx}] No decel onset detected; latency set to 0.")
            t_sys_resp = np.nan

        t_request = time[aeb_start_idx]
        dead_time = float(t_sys_resp - t_request) if np.isfinite(t_sys_resp) else 0.0
        resp_time = float(t_sys_resp) if np.isfinite(t_sys_resp) else 0.0
        return {"resp_time": round(resp_time, 3), "dead_time": round(dead_time, 3)}

    # ------------------------------------------------------------------
    # Communication latency (PB→FB transition)
    # ------------------------------------------------------------------
    def _compute_communication_latency(self, mdf, row_idx):
        """
        Compute communication latency:
        1. Detect partial braking (PB) phase sustained for ≥ pb_duration.
        2. Detect transition to full braking (FB).
        3. Define PB→FB transition as communication start time.
        4. Search within a time window after FB for actual decel onset
            (knee point) based on jerk threshold.
        5. Latency = (decel knee time) - (PB→FB transition time)
        """
        time = np.asarray(mdf.time)
        tgt_decel = np.asarray(mdf.aebTargetDecel)
        accel = np.asarray(mdf.longActAccelFlt)

        # --- Step 1: detect partial braking (PB) phase sustained for ≥ pb_duration
        mask_pb = tgt_decel == self.pb_tgt_decel
        pb_indices = np.where(mask_pb)[0]
        if len(pb_indices) == 0:
            warnings.warn(f"[Row {row_idx}] No partial braking phase; commLatency=0.")
            return {"comm_latency": 0.0}

        dt = np.mean(np.diff(time)) if len(time) > 1 else 0.01
        required_samples = int(self.pb_duration / dt)

        # Continuous PB segments
        pb_segments = np.split(pb_indices, np.where(np.diff(pb_indices) != 1)[0] + 1)
        sustained_pb = [seg for seg in pb_segments if len(seg) >= required_samples]
        if not sustained_pb:
            warnings.warn(f"[Row {row_idx}] PB duration < {self.pb_duration}s; commLatency=0.")
            return {"comm_latency": 0.0}

        pb_end_idx = sustained_pb[0][-1]

        # --- Step 2: find FB (full braking) transition
        fb_candidates = np.where(tgt_decel[pb_end_idx:] == self.fb_tgt_decel)[0]
        if len(fb_candidates) == 0:
            warnings.warn(f"[Row {row_idx}] No FB transition; commLatency=0.")
            return {"comm_latency": 0.0}

        fb_start_idx = pb_end_idx + fb_candidates[0]
        t_pb_fb = time[fb_start_idx]  # PB→FB transition timestamp

        # --- Step 3: define detection window after FB
        end_idx = min(fb_start_idx + self.latency_window_samples, len(time) - 1)
        if fb_start_idx >= end_idx:
            warnings.warn(f"[Row {row_idx}] Invalid latency window after FB; commLatency=0.")
            return {"comm_latency": 0.0}

        # --- Step 4: find knee point (vehicle response)
        jerk = np.gradient(accel[fb_start_idx:end_idx + 1], time[fb_start_idx:end_idx + 1])
        resp_idx_rel = detect_decel_onset(jerk, self.neg_thd)

        if resp_idx_rel is None:
            warnings.warn(f"[Row {row_idx}] No decel onset detected after FB; commLatency=0.")
            return {"comm_latency": 0.0}

        resp_idx_abs = fb_start_idx + resp_idx_rel
        t_decel_knee = time[resp_idx_abs]

        # --- Step 5: compute latency
        comm_latency = max(t_decel_knee - t_pb_fb, 0.0)

        print(
            f"🛰️ [Row {row_idx}] Communication Latency:\n"
            f"   • PB→FB transition @ {t_pb_fb:.3f} s (idx={fb_start_idx})\n"
            f"   • Decel knee       @ {t_decel_knee:.3f} s (idx={resp_idx_abs})\n"
            f"   → commLatency = {comm_latency:.3f} s\n"
        )

        return {"comm_latency": round(comm_latency, 3)}
