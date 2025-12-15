# 🚗 ADAS KPI Processing Pipelines

End-to-end tooling for extracting and visualizing ADAS KPIs from MF4 logs. Supports longitudinal (AEB, FCW, LSAEB) and lateral (LKA) features, event-level KPIs, cycle/availability KPIs, and interactive Plotly visualizations.

---

## 📦 Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## ▶️ Run
- Interactive chooser (includes GUI option): `python3 -m src.run_kpi_tool`
- GUI directly (PySide6): `python3 -m src.gui.app`  
  Select MF4 file(s) from the same folder → pick pipeline (AS Long/Lat) → logs stream into the window while each file runs sequentially.
- CLI pipelines:  
  - `python3 -m src.as_long_pipeline`   # AEB + FCW + LSAEB  
  - `python3 -m src.as_lat_pipeline`    # LKA  
  Both prompt for an MF4 folder if paths are not provided programmatically.
Configs: `src/config/config_as_long.json` and `src/config/config_as_lat.json`.

Outputs (per run) under `rawdata/analysis_results/`:
- `*_kpi_results.xlsx` with event sheets (`aeb`, `fcw`, `lsaeb`, `lka`) plus shared `cycleKPI`.
- HTML plots per feature in subfolders (e.g., `analysis_results/aeb/`).

---

## 🧭 Workflow
1) **Config load** (`src/config/config.py`)  
   Reads JSON + Excel (signal map, graphSpec, lineColors, markerShapes, KPI schemas, calibratables).
2) **Signal extraction** (`src/pipeline/input_handler.py`)  
   Parses MF4, maps signals, writes extracted MF4 chunks and `.mat` files.
3) **Event detection** (`src/pipeline/base/base_event_segmenter.py` subclasses)  
   Splits logs into per-event chunks (AEB/FCW/LSAEB/LKA).
4) **KPI extraction**  
   - Event KPIs via `BaseEventKpiExtractor` subclasses.  
   - Cycle/availability KPIs via `BaseCycleKpiExtractor` subclasses.  
   Exported into `*_kpi_results.xlsx`.
5) **Visualization**  
   `src/viz` renders Matplotlib → Plotly HTML (calibrations, averages, legend ordering).

---

## 📂 Key Modules
- `src/config/` — configs, enum definitions, KPI schemas.
- `src/pipeline/` — domain pipelines, event/cycle extractors, visualizers.
- `src/viz/` — plotter registry, exporters, figure/style/filter managers.
- `src/utils/` — IO helpers, KPI table builders, path utilities.

---

## 🗂️ Outputs & Sheets
- Event KPIs: per-feature sheets (`aeb`, `fcw`, `lsaeb`, `lka`).
- Cycle KPIs: combined `cycleKPI` sheet keyed by `label` + `feature` so multiple features coexist.
- Plots: HTML in `analysis_results/<feature>/Fig_## - <title>.html`.

---

## 🧪 Quick Checks
```bash
python3 -m src.run_kpi_tool
# verify analysis_results contains updated Excel and HTML outputs
```

---

## 🛠️ Notes
- Requirements: see `requirements.txt` (asammdf, numpy/pandas/scipy, matplotlib/plotly, openpyxl, PyYAML, pyinstaller, etc.).
- Keep config Excel/JSON in `src/config/` aligned with signal maps, graph specs, and KPI definitions.
