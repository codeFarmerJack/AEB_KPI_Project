import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.base.base_event_segmenter import BaseEventSegmenter


class _DummyMDF:
    def __init__(self, data):
        self._data = data

    def get(self, name):
        if name not in self._data:
            raise AttributeError(name)

        return SimpleNamespace(samples=np.asarray(self._data[name]))


class _DummySegmenter(BaseEventSegmenter):
    signal_name = "sig"

    def __init__(self, input_handler):
        super().__init__(input_handler, event_name="dummy")
        self.detect_called = False
        self.extract_called = False
        self.detect_args = None
        self.extract_args = None

    def detect_events(self, time, signal):
        self.detect_called = True
        self.detect_args = (time, signal)
        return np.array([0.5]), np.array([1.5])

    def extract_events(self, mdf, start_times, end_times, name):
        self.extract_called = True
        self.extract_args = (start_times, end_times, name)


def test_process_all_files_calls_detect_and_extract(tmp_path, monkeypatch):
    extracted_dir = tmp_path / "extracted"
    extracted_dir.mkdir()
    (extracted_dir / "file_extracted.mf4").write_text("", encoding="utf-8")

    input_handler = SimpleNamespace(
        in_path_raw_data=str(tmp_path),
        out_path_extracted=str(extracted_dir),
    )
    segmenter = _DummySegmenter(input_handler)

    dummy_mdf = _DummyMDF({"time": [0.0, 1.0, 2.0], "sig": [0, 1, 0]})
    monkeypatch.setattr(
        "src.pipeline.base.base_event_segmenter.safe_load_mdf",
        lambda _path: dummy_mdf,
    )

    segmenter.process_all_files()

    assert segmenter.detect_called is True
    assert segmenter.extract_called is True
    assert segmenter.detect_args[0].tolist() == [0.0, 1.0, 2.0]
    assert segmenter.detect_args[1].tolist() == [0, 1, 0]
    assert segmenter.extract_args[2] == "file_extracted"
