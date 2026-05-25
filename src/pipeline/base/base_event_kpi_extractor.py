import os
import warnings

import numpy as np

from src.utils.signal_mdf import SignalMDF, get_signal
from src.utils.create_kpi_table import create_kpi_table_from_df
from src.utils.output_naming import build_kpi_result_filename
from src.utils.exporter import export_kpi_to_excel


class BaseEventKpiExtractor:
    """
    Base class for event KPI extractors (AEB, FCW, etc.).

    Criteria: KPIs are extracted per MF4 event chunk, while the subclass
    defines what constitutes a valid event and which signals/thresholds
    are required to compute KPIs.
    """

    FEATURE_NAME = "BASE"
    PARAM_SPECS = {}
    _EVENT_EXT = ".mf4"

    # ------------------------------------------------------------------ #
    def __init__(self, config, event_segmenter, chunk_attr_name, feature_name=None):
        self._validate_inputs(config, event_segmenter, chunk_attr_name)
        self.feature_name = feature_name or self.FEATURE_NAME
        self.config = config
        self._init_paths(event_segmenter, chunk_attr_name)
        self.file_list = self._collect_event_files(self.out_path_chunks)
        self.kpi_table = self._init_kpi_table(config)
        self._load_params(config)

    # ------------------------------------------------------------------ #
    def _load_params(self, config):
        """Load default parameters and apply overrides from config.params."""
        cls_name = self.__class__.__name__
        print(f"\n⚙️ Loading parameters for {cls_name}...")

        self._apply_param_defaults()
        self._apply_param_overrides(getattr(config, "params", {}))

    def _apply_param_defaults(self):
        for name, spec in self.PARAM_SPECS.items():
            default_val = spec.get("default")
            setattr(self, name, default_val)
            print(f"   • {name:<18} ← {default_val} (default)")

    def _apply_param_overrides(self, params):
        for name, spec in self.PARAM_SPECS.items():
            # try both param name and param_name_<feature>
            keys = [name, f"{name}_{self.feature_name.lower()}"]
            for key in keys:
                if key in params:
                    try:
                        val = spec.get("type", float)(params[key])
                        setattr(self, name, val)
                        print(f"   ✅ {name:<18} overridden ← {val} (from '{key}')")
                        break
                    except Exception as e:
                        warnings.warn(f"⚠️ Could not parse {key}: {e}")

    # ------------------------------------------------------------------ #
    def _load_mdf(self, fpath):
        """Load MDF file safely."""
        try:
            return SignalMDF(fpath)
        except Exception as e:
            warnings.warn(f"⚠️ Failed to read {os.path.basename(fpath)}: {e}")
            return None

    def _prepare_time(self, mdf):
        """Extract or synthesize a time vector."""
        time = get_signal(mdf, "time")
        if time is not None and len(time) > 0:
            if getattr(mdf, "_time_is_synthesized", False):
                step_s = self._get_resample_interval_s()
                warnings.warn(
                    f"⚠️ Rebuilt synthesized time vector using configured resample_rate={step_s}s."
                )
                return np.arange(len(time), dtype=float) * step_s
            return np.asarray(time, dtype=float)

        try:
            time = mdf.get_master(0).flatten()
            if time is not None and len(time) > 0:
                return np.asarray(time, dtype=float)
        except Exception:
            pass

        n = len(mdf.groups[0].channels[0].samples) if mdf.groups else 0
        step_s = self._get_resample_interval_s()
        warnings.warn(
            f"⚠️ Synthesized time vector using configured resample_rate={step_s}s."
        )
        return np.arange(n, dtype=float) * step_s

    def _get_resample_interval_s(self):
        params = getattr(self.config, "params", {}) or {}
        if isinstance(params, dict):
            for key in ("resample_rate", "RESAMPLE_RATE"):
                if key in params:
                    try:
                        step_s = float(params[key])
                        if step_s > 0:
                            return step_s
                    except Exception:
                        pass
        return 0.01

    def _insert_label(self, index, fname):
        """Ensure label column exists and assign filename."""
        if "label" not in self.kpi_table.columns:
            self.kpi_table.insert(0, "label", "")
        self.kpi_table.loc[index, "label"] = fname

    def _select_event_indices(self, event_indices, n_samples):
        start_indices, end_indices = event_indices
        start_idx = int(start_indices[0])
        end_idx = int(end_indices[0]) if len(end_indices) else n_samples - 1

        start_idx = max(0, min(start_idx, n_samples - 1))
        end_idx = max(0, min(end_idx, n_samples - 1))
        return start_idx, end_idx

# ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, index):
        """Subclasses must implement and return a dict of KPI values."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement extract_event_kpis()"
        )

    def _extract_single_event_by_indices(self, mdf, fname, index):
        signals = self._load_signals(mdf, fname)
        if signals is None:
            return None

        if self._should_skip_event(signals, fname):
            return None

        event_indices = self._detect_events(signals, fname)
        if event_indices is None:
            return None

        start_idx, end_idx = self._select_event_indices(event_indices, len(signals.time))
        result = self._build_event_result(signals, start_idx, end_idx)
        self._post_process_event_by_indices(mdf, index, signals, start_idx, end_idx, result)
        return result

    def _extract_single_event_by_time(self, mdf, fname, index):
        signals = self._load_signals(mdf, fname)
        if signals is None:
            return None

        event_time = self._detect_event_time(signals, fname)
        if event_time is None:
            return None

        result = self._build_event_result(signals, event_time)
        self._post_process_event_by_time(mdf, index, signals, event_time, result)
        return result

    def _should_skip_event(self, signals, fname):
        return False

    def _post_process_event_by_indices(self, mdf, index, signals, start_idx, end_idx, result):
        return None

    def _post_process_event_by_time(self, mdf, index, signals, event_time, result):
        return None

    # ------------------------------------------------------------------ #
    def export_event_kpis(self, sheet_name=None):
        """
        Export ONLY event-based KPIs to Excel.
        Cycle/availability KPIs are handled by cycle extractors.
        """
        event_sheet = (sheet_name or self.feature_name).lower()

        output_path = self._event_output_path()
        df_main = self.kpi_table.copy()

        # Sort BEFORE export
        if "vehSpd" in df_main.columns:
            df_main = df_main.sort_values("vehSpd")

        export_kpi_to_excel(df_main, output_path, sheet_name=event_sheet)

        print(f"📄 Exported EVENT KPIs → sheet '{event_sheet}' in {output_path}")

    # ------------------------------------------------------------------ #
    def process_mdf_events(self):
        """
        Unified loop for all event-based KPI extractors (AEB, FCW, LSAEB, etc.)
        Subclasses must implement extract_event_kpis(mdf, fname, index)
        which returns a dict of KPI values.
        """

        for i, fname in enumerate(self.file_list):
            self._process_event_file(i, fname)

        self._finalize_event_table()

    def _validate_inputs(self, config, event_segmenter, chunk_attr_name):
        if config is None or event_segmenter is None:
            raise ValueError("Both Config and EventSegmenter are required.")
        if not hasattr(event_segmenter, chunk_attr_name):
            raise TypeError(f"event_segmenter missing required attribute '{chunk_attr_name}'")

    def _init_paths(self, event_segmenter, chunk_attr_name):
        self.in_path_raw_data = event_segmenter.in_path_raw_data
        self.out_path_base = getattr(
            event_segmenter,
            "out_path_base",
            os.path.join(self.in_path_raw_data, "kpi_parser"),
        )
        self.out_path_results = os.path.join(self.out_path_base, "analysis_results")
        os.makedirs(self.out_path_results, exist_ok=True)
        self.in_path_extracted = event_segmenter.in_path_extracted
        self.out_path_chunks = getattr(event_segmenter, chunk_attr_name)
        self.selected_mf4_files = getattr(event_segmenter, "selected_mf4_files", None)
        self.config.kpi_result_filename = build_kpi_result_filename(
            getattr(self.config, "kpi_result_filename", "kpi_results.xlsx"),
            self.selected_mf4_files,
        )

    def _collect_event_files(self, path):
        files = [f for f in os.listdir(path) if f.endswith(self._EVENT_EXT)]
        if not files:
            warnings.warn(f"No {self._EVENT_EXT} event files found in {path}; skipping event KPIs.")
            return []
        return files

    def _init_kpi_table(self, config):
        return create_kpi_table_from_df(config.event_kpi_list, feature=self.feature_name)

    def _event_output_path(self):
        filename = getattr(self.config, "kpi_result_filename", "kpi_results.xlsx")
        return os.path.join(self.out_path_results, filename)

    def _process_event_file(self, index, fname):
        fpath = os.path.join(self.out_path_chunks, fname)
        self._insert_label(index, fname)
        mdf = self._load_mdf(fpath)
        if mdf is None:
            return

        result = self.extract_event_kpis(mdf, fname, index)
        if result is None:
            return

        for key, value in result.items():
            self.kpi_table.loc[index, key] = value

    def _finalize_event_table(self):
        self.kpi_table = self.kpi_table.round(3)
        print(f"\n✅ {self.feature_name} Event KPI extraction completed successfully.")
