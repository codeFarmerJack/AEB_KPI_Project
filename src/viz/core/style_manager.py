# src/viz/core/style_manager.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class StyleManager:
    """
    Provides markers and colors in a deterministic, cyclic way.
    """

    def __init__(self, marker_shapes, line_colors):
        self.marker_shapes = self._normalize_markers(marker_shapes)
        self.line_colors = line_colors

    def _normalize_markers(self, marker_df_or_list):
        if isinstance(marker_df_or_list, pd.DataFrame):
            cols = [c for c in marker_df_or_list.columns if c.strip().lower() == "shapes"]
            if cols:
                col = cols[0]
                shapes = (
                    marker_df_or_list[col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .tolist()
                )
            else:
                shapes = ["o", "s", "^", "D"]
        elif isinstance(marker_df_or_list, (list, tuple, np.ndarray)):
            shapes = list(marker_df_or_list)
        else:
            shapes = ["o", "s", "^", "D"]

        return shapes or ["o"]

    def get_marker_and_color(self, idx: int):
        # marker
        m_idx = idx % len(self.marker_shapes)
        marker = self.marker_shapes[m_idx]

        # color
        if isinstance(self.line_colors, pd.DataFrame):
            cols = [c.strip().lower() for c in self.line_colors.columns]
            if all(c in cols for c in ["r", "g", "b"]):
                # enforce [r,g,b]
                self.line_colors.columns = cols
                rgb = self.line_colors[["r", "g", "b"]].to_numpy(dtype=float)
                c_idx = idx % len(rgb)
                color = tuple(rgb[c_idx])
            else:
                color = plt.cm.tab10(idx % 10)
        elif isinstance(self.line_colors, (list, np.ndarray)):
            color = self.line_colors[idx % len(self.line_colors)]
        else:
            color = plt.cm.tab10(idx % 10)

        return marker, color
