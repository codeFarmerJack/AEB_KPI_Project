import os
import sys
from pathlib import Path

import numpy as np

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


def test_offset_path_differs_from_base(tmp_path):
    out_dir = _get_out_dir(tmp_path)
    viz = AebCycleVisualizer(out_dir=str(out_dir))
    lon = np.array([0.0, 1.0, 2.0], dtype=float)
    lat = np.array([0.0, 0.0, 0.0], dtype=float)

    offset_path = viz._compute_offset_path(lon, lat)

    assert offset_path is not None
    offset_lon, offset_lat = offset_path
    assert len(offset_lon) == len(lon)
    assert not np.allclose(offset_lat, lat, equal_nan=True)


def test_aeb_fb_path_has_legend_and_connectgaps(tmp_path):
    out_dir = _get_out_dir(tmp_path)
    viz = AebCycleVisualizer(out_dir=str(out_dir))
    signals = {
        "time": np.array([0, 1, 2, 3, 4], dtype=float),
        "lon": np.array([0.0, 1.0, np.nan, 3.0, 4.0], dtype=float),
        "lat": np.array([0.0, 0.5, np.nan, 1.5, 2.0], dtype=float),
        "speed": np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=float),
        "aebFullState": np.array([1, 1, 2, 2, 1], dtype=float),
        "longGap": np.zeros(5, dtype=float),
    }

    viz.plot_cycle({}, signals, title="AEB FB Test")

    out_file = out_dir / "AEB_FB_Test.html"
    assert out_file.exists()
    html = out_file.read_text(encoding="utf-8")
    assert "aeb-fb:" in html
    assert '"connectgaps":true' in html or '"connectgaps": true' in html
