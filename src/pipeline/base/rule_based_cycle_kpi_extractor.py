import warnings
from types import SimpleNamespace

import numpy as np

from src.pipeline.base.base_cycle_kpi_extractor import BaseCycleKpiExtractor
from src.utils.process_calibratables import interpolate_threshold_clamped
from src.utils.signal_mdf import get_signal


class RuleBasedCycleKpiExtractor(BaseCycleKpiExtractor):
    """
    Shared distance-weighted cycle KPI engine.

    Subclasses declare signal aliases and KPI rules instead of re-implementing
    the same distance, threshold, and percentage logic.
    """

    SIGNAL_SPECS = {}
    METRIC_SPECS = ()
    OUTPUT_FEATURE_MODE = "self"
    DISTANCE_TIME_FIELD = "time"
    DISTANCE_SPEED_FIELD = "speed_mps"
    ROUND_DIGITS = 2

    def extract_cycle_kpis(self, mdf, fname):
        signals = self._load_rule_signals(mdf)
        if signals is None:
            return {}

        time = getattr(signals, self.DISTANCE_TIME_FIELD, None)
        speed = getattr(signals, self.DISTANCE_SPEED_FIELD, None)
        if time is None or speed is None:
            warnings.warn(
                f"⚠️ Missing distance inputs '{self.DISTANCE_TIME_FIELD}' or "
                f"'{self.DISTANCE_SPEED_FIELD}' for {self.FEATURE_NAME}."
            )
            return {}

        dist, total_dist = self._compute_distance_profile(time, speed)
        metrics = self._compute_metrics(signals, dist, total_dist)
        rounded = self._round_metrics(metrics, digits=self.ROUND_DIGITS)
        return {feature: dict(rounded) for feature in self._output_features()}

    def _load_rule_signals(self, mdf):
        missing = []
        values = {}

        for field, spec in self.SIGNAL_SPECS.items():
            signal_name = spec["signal"]
            required = spec.get("required", True)
            default = spec.get("default")
            transform = spec.get("transform")

            try:
                value = get_signal(mdf, signal_name, required=required)
            except AttributeError:
                if required:
                    missing.append(signal_name)
                value = default

            if value is None and required:
                missing.append(signal_name)

            if value is not None and transform is not None:
                value = transform(value)

            values[field] = value

        if missing:
            deduped = ", ".join(sorted(set(missing)))
            warnings.warn(f"Missing required {self.FEATURE_NAME} signals: {deduped}")
            return None

        return SimpleNamespace(**values)

    def _compute_distance_profile(self, time, speed_mps):
        dt = np.diff(time, prepend=time[0])
        dt = np.maximum(dt, 0.0)
        dist = np.asarray(speed_mps, dtype=float) * dt
        return dist, float(dist.sum())

    def _compute_metrics(self, signals, dist, total_dist):
        if total_dist <= 0:
            warnings.warn("⚠️ Total distance is zero; cycle KPIs will be filled with 0.0.")
            return {spec["key"]: 0.0 for spec in self.METRIC_SPECS}

        metrics = {}
        for spec in self.METRIC_SPECS:
            metrics[spec["key"]] = self._compute_metric_value(spec, signals, dist, total_dist)
        return metrics

    def _compute_metric_value(self, spec, signals, dist, total_dist):
        if "constant" in spec:
            return spec["constant"]

        mask = spec.get("mask")
        if callable(mask):
            resolved_mask = mask(signals)
            return self._dist_pct_from_mask(dist, total_dist, resolved_mask)

        signal = getattr(signals, spec["signal"], None)
        threshold = self._resolve_threshold(spec, signals)
        resolved_mask = self._mask_for_op(signal, threshold, spec["op"])
        return self._dist_pct_from_mask(dist, total_dist, resolved_mask)

    def _resolve_threshold(self, spec, signals):
        if "calibratable" in spec:
            speed = getattr(signals, self.DISTANCE_SPEED_FIELD, None)
            return self._interp_calibratable(spec["calibratable"], speed)
        return spec.get("threshold")

    def _interp_calibratable(self, name, speed_mps):
        cal = (getattr(self.config, "calibratables_interp", None) or {}).get(name)
        if cal is None:
            cal = (self.config.calibratables or {}).get(name)
        if cal is None:
            return None
        try:
            return interpolate_threshold_clamped(cal, speed_mps)
        except Exception as exc:
            warnings.warn(f"⚠️ Failed to interpolate calibratable '{name}': {exc}")
            return None

    def _mask_for_op(self, signal, threshold, op):
        if signal is None or threshold is None:
            return None

        signal_arr = np.asarray(signal, dtype=float)
        threshold_arr = np.asarray(threshold, dtype=float)

        if op == "abs_gt":
            return np.abs(signal_arr) > threshold_arr
        if op == "lt":
            return signal_arr < threshold_arr
        if op == "eq":
            return signal_arr == threshold_arr
        raise ValueError(f"Unsupported op '{op}'")

    def _dist_pct_from_mask(self, dist, total_dist, mask):
        if mask is None or total_dist <= 0:
            return np.nan
        mask_arr = np.asarray(mask, dtype=bool)
        return float(np.sum(dist[mask_arr]) / total_dist * 100)

    def _round_metrics(self, metrics, digits=2):
        return {key: self._round_pct(value, digits) for key, value in metrics.items()}

    def _round_pct(self, value, digits):
        if value is None:
            return np.nan
        try:
            if np.isnan(value):
                return np.nan
        except TypeError:
            return value
        return float(np.round(value, digits))

    def _output_features(self):
        if self.OUTPUT_FEATURE_MODE == "schema":
            features = self.get_configured_features(include_common=False)
            return features or [self.FEATURE_NAME]
        return [self.FEATURE_NAME]
