# src/viz/core/figure_manager.py
import matplotlib.pyplot as plt


class FigureManager:
    """
    Manages matplotlib figures/axes keyed by graph title.
    Also owns the per-figure label ledger used later by Exporter
    to order Plotly legends.
    """

    def __init__(self):
        self._fig_cache = {}      # title -> (fig, ax)
        self._draw_labels = {}    # title -> [labels in draw order]

    # ------------ creation / reuse ------------ #
    def get_or_create(self, title: str, graph_spec, is_new: bool = False):
        if title in self._fig_cache and not is_new:
            fig, ax = self._fig_cache[title]
            return fig, ax, False

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.set_title(title)
        ax.grid(True, which="both", linestyle="--", alpha=0.5)

        # Use row 0 as X-axis spec (same as your old logic)
        x_label = str(graph_spec.loc[0, "axis_name"])
        ax.set_xlabel(x_label.replace("_", " "))

        try:
            x_min = float(graph_spec.loc[0, "min_axis_value"])
            x_max = float(graph_spec.loc[0, "max_axis_value"])
            ax.set_xlim(x_min, x_max)
        except Exception:
            pass

        self._fig_cache[title] = (fig, ax)
        self._draw_labels[title] = []
        return fig, ax, True

    # ------------ label ledger ------------ #
    def add_label(self, title: str, label: str) -> None:
        if not label:
            return
        self._draw_labels.setdefault(title, []).append(label)

    def get_labels(self, title: str):
        return list(self._draw_labels.get(title, []))

    def clear_labels(self, title: str):
        self._draw_labels.pop(title, None)

    # ------------ cleanup ------------ #
    def pop(self, title: str):
        return self._fig_cache.pop(title, (None, None))

    def close(self, title: str):
        fig, _ = self.pop(title)
        if fig is not None:
            plt.close(fig)
        self.clear_labels(title)
