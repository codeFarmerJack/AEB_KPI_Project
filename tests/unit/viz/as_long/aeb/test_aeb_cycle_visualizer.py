import os
import sys
from pathlib import Path

import numpy as np
from plotly.subplots import make_subplots

PROJECT_ROOT = Path(__file__).resolve().parents[5]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.as_long.aeb.aeb_cycle_visualizer import AebCycleVisualizer


def _get_out_dir(tmp_path):
    out_dir = os.environ.get("AEB_TEST_OUTDIR")
    if out_dir:
        path = Path(out_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(__file__).resolve().parent


def test_aeb_path_uses_base_coords_without_offset(tmp_path):
    out_dir = _get_out_dir(tmp_path)
    viz = AebCycleVisualizer(out_dir=str(out_dir))
    viz.path_smoothing = {"enabled": False}
    lon = np.array([0.0, 1.0, 2.0], dtype=float)
    lat = np.array([0.0, 0.5, 1.0], dtype=float)
    signals = {
        "lon": lon,
        "lat": lat,
        "aebFullState": np.array([1, 1, 1], dtype=float),
    }

    fig = make_subplots(rows=1, cols=1)
    viz._plot_path_state(fig, signals, row=1, col=1, signal_name="aebFullState")

    assert len(fig.data) == 1
    trace = fig.data[0]
    assert np.allclose(trace["x"], lon, equal_nan=True)
    assert np.allclose(trace["y"], lat, equal_nan=True)


def test_aeb_fb_path_has_legend_and_connectgaps(tmp_path):
    out_dir = _get_out_dir(tmp_path)
    viz = AebCycleVisualizer(out_dir=str(out_dir))
    signals = {
        "time": np.array([0, 1, 2, 3, 4], dtype=float),
        "lon": np.array([0.0, 1.0, np.nan, 3.0, 4.0], dtype=float),
        "lat": np.array([0.0, 0.5, np.nan, 1.5, 2.0], dtype=float),
        "speed": np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=float),
        "aebFullState": np.array([1, 1, 2, 2, 1], dtype=float),
        "aebPartialState": np.array([0, 1, 1, 2, 2], dtype=float),
        "longGap": np.zeros(5, dtype=float),
    }

    viz.plot_cycle({}, signals, title="AEB FB Test")

    out_file = out_dir / "AEB_FB_Test.html"
    assert out_file.exists()
    html = out_file.read_text(encoding="utf-8")
    assert "aeb-fb:" in html
    assert "aeb-pb:" in html
    assert '"connectgaps":true' in html or '"connectgaps": true' in html
