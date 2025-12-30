import os
import warnings

import numpy as np

from src.utils.signal_mdf import SignalMDF, get_signal
from src.utils.create_kpi_table import create_kpi_table_from_df
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
        if time is None or len(time) == 0:
            try:
                time = mdf.get_master(0).flatten()
            except Exception:
                n = len(mdf.groups[0].channels[0].samples) if mdf.groups else 0
                time = np.arange(n, dtype=float)
            warnings.warn("⚠️ Synthesized time vector (equidistant).")
        return time

    def _insert_label(self, index, fname):
        """Ensure label column exists and assign filename."""
        if "label" not in self.kpi_table.columns:
            self.kpi_table.insert(0, "label", "")
        self.kpi_table.loc[index, "label"] = fname

# ------------------------------------------------------------------ #
    def extract_event_kpis(self, mdf, fname, index):
        """Subclasses must implement and return a dict of KPI values."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement extract_event_kpis()"
        )

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
        self.out_path_results = os.path.join(self.in_path_raw_data, "analysis_results")
        os.makedirs(self.out_path_results, exist_ok=True)
        self.in_path_extracted = event_segmenter.in_path_extracted
        self.out_path_chunks = getattr(event_segmenter, chunk_attr_name)

    def _collect_event_files(self, path):
        files = [f for f in os.listdir(path) if f.endswith(self._EVENT_EXT)]
        if not files:
            raise FileNotFoundError(f"No {self._EVENT_EXT} files found in {path}")
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
