import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.input_handler import InputHandler


def _make_config():
    return SimpleNamespace(signal_map=pd.DataFrame(), params={})


def test_collect_mf4_paths_from_folder(tmp_path):
    (tmp_path / "a.mf4").write_text("", encoding="utf-8")
    (tmp_path / "b.MF4").write_text("", encoding="utf-8")
    (tmp_path / "c.txt").write_text("", encoding="utf-8")

    handler = InputHandler(_make_config(), input_path=tmp_path)
    paths = handler._collect_mf4_paths()
    names = sorted(p.name for p in paths)

    assert names == ["a.mf4", "b.MF4"]


def test_input_handler_uses_provided_files(tmp_path):
    f1 = tmp_path / "one.mf4"
    f2 = tmp_path / "two.mf4"
    f1.write_text("", encoding="utf-8")
    f2.write_text("", encoding="utf-8")

    handler = InputHandler(_make_config(), input_path=tmp_path, mf4_files=[str(f1), str(f2)])

    assert handler.in_path_raw_data == str(tmp_path)
    assert sorted(handler._provided_files) == sorted([str(f1), str(f2)])

    paths = handler._collect_mf4_paths()
    assert sorted(p.name for p in paths) == ["one.mf4", "two.mf4"]


def test_build_signal_fallback_categorical(tmp_path):
    handler = InputHandler(_make_config(), input_path=tmp_path)
    series = pd.Series(["b", "a", "b"], index=[0, 1, 2], dtype=object)

    sig = handler._build_signal("unknownSignal", series)

    assert sig.samples.tolist() == [1, 0, 1]
    assert np.all(sig.timestamps == series.index.values)
