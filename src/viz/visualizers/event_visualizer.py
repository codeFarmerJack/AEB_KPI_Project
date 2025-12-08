import warnings

from src.pipeline.base.base_visualizer import BaseVisualizer
from src.viz.registry import get_plotter_class


class EventVisualizer(BaseVisualizer):
    """
    Generic event KPI visualizer.

    One instance per feature, e.g.:
        AEB:  EventVisualizer(config, extractor, feature="aeb")
        FCW:  EventVisualizer(config, extractor, feature="fcw")
    """

    def __init__(self, config, kpi_extractor, feature: str):
        super().__init__(config, kpi_extractor, feature=feature)

        self.graph_spec = self.filter_graph_spec()
        self.graph_spec = self._normalize_graph_spec(self.graph_spec)
        self._group_counter = iter(range(1, 201))
        self.interactive = getattr(config, "interactive", False)

        print(f"🎯 EventVisualizer initialized for feature '{self.feature}'.")

    # -------------------------------------------------------- #
    @staticmethod
    def _normalize_graph_spec(gs):
        if gs is None:
            return gs
        gs = gs.loc[:, ~gs.columns.str.contains("^unnamed")]
        gs.columns = (
            gs.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )
        return gs

    # -------------------------------------------------------- #
    def plot(self):
        if self.graph_spec is None or self.graph_spec.empty:
            warnings.warn("⚠️ graph_spec is empty for this feature — skipping.")
            return

        num_rows = len(self.graph_spec)
        print(f"📊 Found {num_rows} graph rows for '{self.feature.upper()}'.\n")

        plotters = {}

        for idx in range(1, num_rows):
            plot_type = str(self.graph_spec.loc[idx, "plottype"]).strip().lower()
            title = str(self.graph_spec.loc[idx, "title"]).strip()
            print(f"🎨 Plotting [{plot_type.upper()}] row {idx} — '{title}'")

            try:
                plotter_cls = get_plotter_class(plot_type)
                if plotter_cls is None:
                    warnings.warn(
                        f"⚠️ Unsupported plot type '{plot_type}' at row {idx}. Skipping."
                    )
                    continue

                if plot_type not in plotters:
                    plotters[plot_type] = plotter_cls(self)

                plotters[plot_type].plot_row(idx)
            except Exception as e:
                warnings.warn(f"⚠️ Plotting failed at row {idx}: {e}")

        print(f"✅ Event visualization complete for '{self.feature.upper()}'.")
