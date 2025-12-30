# 🚗 ADAS KPI Processing Pipelines

End-to-end tooling for extracting and visualizing ADAS KPIs from MF4 logs. Supports longitudinal (AEB, FCW, LSAEB) and lateral (LKA) features, event-level KPIs, cycle/availability KPIs, and interactive Plotly visualizations.

---

## 📦 Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
PySide6 is included in `requirements.txt` for the GUI; on some systems you may need Qt platform plugins (X11/Wayland on Linux, or ensure Xcode Command Line Tools on macOS).

---

## ▶️ Run
- GUI (PySide6): `python3 -m src.gui.app`  
  Select MF4 folder → pick features → hit RUN; logs stream into the window as each feature runs sequentially.
- Compatibility entrypoint: `python3 -m src.run_kpi_tool` (launches the same GUI).
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
- `src/gui/` — PySide6 desktop UI (folder selection, feature toggles, runner).
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

## 📦 Build Executable (PyInstaller)
Ensure dependencies are installed (`pip install -r requirements.txt`), then build from repo root:
```bash
pyinstaller run_kpi_tool.spec
```
Artifacts:
- `dist/ADAS_KPI_Tool/` directory bundle (contains CLI + GUI).
- On macOS, a `.app` bundle is also produced.
If the GUI fails to start due to Qt plugins, verify `PySide6` is installed and rerun the build; the spec already collects PySide6, pyecharts, and Qt data.

---

## 🛠️ Notes
- Requirements: see `requirements.txt` (asammdf, numpy/pandas/scipy, matplotlib/plotly/pyecharts, openpyxl, PyYAML, pyinstaller, etc.).
- Keep config Excel/JSON in `src/config/` aligned with signal maps, graph specs, and KPI definitions.
