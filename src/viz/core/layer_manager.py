# src/viz/core/layer_manager.py
import numpy as np
import warnings


class LayerManager:
    """
    Adds 'layers' on top of base plots:
    - average horizontal lines
    - calibration curves
    """

    def __init__(self, calibratables: dict):
        self.calibratables = calibratables or {}

    # ---------- average line ---------- #
    def add_average_line(self, ax, legend_name: str, y_vals):
        if y_vals is None or len(y_vals) == 0:
            return None

        y_vals = np.asarray(y_vals, dtype=float)
        if y_vals.size == 0:
            return None

        y_avg = float(np.nanmean(y_vals))
        x_min, x_max = ax.get_xlim()
        label = f"Average {legend_name}: {y_avg:.3f}"

        ax.plot(
            [x_min, x_max],
            [y_avg, y_avg],
            "--",
            color="black",
            linewidth=1.2,
            alpha=0.7,
            label=label,
            zorder=5,
        )
        return label

    # ---------- calibration curves ---------- #
    def add_calibration_limit(self, ax, cal_limit: str):
        if not cal_limit or str(cal_limit).lower() == "none":
            return None

        # case-insensitive key lookup
        cal_key = next(
            (k for k in self.calibratables.keys() if k.lower() == cal_limit.lower()),
            None,
        )
        if not cal_key:
            warnings.warn(f"⚠️ Calibration limit '{cal_limit}' not found.")
            return None

        lim = self.calibratables[cal_key]
        if not (isinstance(lim, dict) and "x" in lim and "y" in lim):
            warnings.warn(f"⚠️ Calibration {cal_limit} found but not in (x,y) format.")
            return None

        ax.plot(
            lim["x"],
            lim["y"],
            "r--",
            linewidth=1.5,
            label=str(cal_key),
        )
        return str(cal_key)
