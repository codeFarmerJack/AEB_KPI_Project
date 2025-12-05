from ..base_plot import BasePlot


class HBarPlotter(BasePlot):
    """
    Horizontal bar plot.

    Expected data dict:
    {
        "labels": [...],         # y-axis categories
        "values": [...],         # bar lengths
        "title": "Optional title",
        "xlabel": "Optional xlabel",
        "ylabel": "Optional ylabel",
    }
    """

    name = "hbar"

    def draw(self, ax, data):
        labels = data["labels"]
        values = data["values"]

        ax.barh(labels, values)

        # Annotate bar ends
        for i, v in enumerate(values):
            ax.text(
                v,
                i,
                f"{v:.1f}",
                va="center",
                ha="left"
            )

        ax.set_title(data.get("title", "Horizontal Bar Plot"))
        ax.set_xlabel(data.get("xlabel", ""))
        ax.set_ylabel(data.get("ylabel", ""))
        ax.grid(True, axis="x")
