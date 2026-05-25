import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.input_handler import InputHandler
from src.utils.mf4_postprocess import build_signal, normalize_source_signals


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
    enum_mapper = SimpleNamespace(get_enum_for_signal=lambda _: None, enums={})
    series = pd.Series(["b", "a", "b"], index=[0, 1, 2], dtype=object)

    sig = build_signal("unknownSignal", series, enum_mapper)

    assert sig.samples.tolist() == [1, 0, 1]
    assert np.all(sig.timestamps == series.index.values)


def test_motion_1_normalization_converts_units_and_derives_requests():
    df = pd.DataFrame(
        {
            "egoSpeed": [36.0],
            "steerWheelAngle": [180.0],
            "steerWheelAngleSpeed": [90.0],
            "yawRate": [45.0],
            "aebTargetDecel": [-6.0],
            "fcwState": [5.0],
        },
        index=[0.0],
    )

    out = normalize_source_signals(df, "motion_1")

    assert np.isclose(out["egoSpeed"].iloc[0], 10.0)
    assert np.isclose(out["steerWheelAngle"].iloc[0], np.pi)
    assert np.isclose(out["steerWheelAngleSpeed"].iloc[0], np.pi / 2)
    assert np.isclose(out["yawRate"].iloc[0], np.pi / 4)
    assert out["aebRequest"].iloc[0] == 1
    assert out["aebPartialState"].iloc[0] == 2
    assert out["aebFullState"].iloc[0] == 1
    assert out["fcwRequest"].iloc[0] == 3
