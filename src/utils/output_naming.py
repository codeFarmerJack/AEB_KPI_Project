from pathlib import Path
import re


def build_kpi_result_filename(base_filename, selected_mf4_files=None):
    """Append MF4 source identity to the workbook name for the current run."""
    base_name = str(base_filename or "kpi_results.xlsx")
    selected = [Path(p) for p in (selected_mf4_files or [])]
    if not selected:
        return base_name

    stem = Path(base_name).stem
    suffix = Path(base_name).suffix or ".xlsx"
    match = re.match(r"^(.*_kpi_results)(?:_.+)?$", stem)
    stem = match.group(1) if match else stem

    if len(selected) == 1:
        mf4_suffix = selected[0].stem
    else:
        mf4_suffix = f"{selected[0].stem}_plus_{len(selected) - 1}_more"

    return f"{stem}_{mf4_suffix}{suffix}"
