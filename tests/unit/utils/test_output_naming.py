import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.output_naming import build_kpi_result_filename


def test_build_kpi_result_filename_appends_single_mf4_stem():
    filename = build_kpi_result_filename(
        "as_long_kpi_results.xlsx",
        ["/tmp/demo_run.mf4"],
    )

    assert filename == "as_long_kpi_results_demo_run.xlsx"


def test_build_kpi_result_filename_is_idempotent_for_same_input():
    once = build_kpi_result_filename(
        "as_long_kpi_results.xlsx",
        ["/tmp/demo_run.mf4"],
    )
    twice = build_kpi_result_filename(
        once,
        ["/tmp/demo_run.mf4"],
    )

    assert twice == once


def test_build_kpi_result_filename_compacts_multiple_files():
    filename = build_kpi_result_filename(
        "as_long_kpi_results.xlsx",
        ["/tmp/demo_run.mf4", "/tmp/second_run.mf4"],
    )

    assert filename == "as_long_kpi_results_demo_run_plus_1_more.xlsx"
