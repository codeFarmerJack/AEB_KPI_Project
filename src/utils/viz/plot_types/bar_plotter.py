from ..base_plot import BasePlot


class BarPlotter(BasePlot):
    """
    Vertical bar plot.

    Expected data dict:
    {
        "labels": [...],          # x-axis categories
        "values": [...],          # heights
        "title": "Optional title",
        "xlabel": "Optional xlabel",
        "ylabel": "Optional ylabel",
    }
    """

    name = "bar"

    def draw(self, ax, data):
        labels = data["labels"]
        values = data["values"]

        bars = ax.bar(labels, values)

        # Annotate each bar with its value
        for b in bars:
            height = b.get_height()
            ax.text(
                b.get_x() + b.get_width() / 2,
                height,
                f"{height:.1f}",
                ha="center",
                va="bottom"
            )

        ax.set_title(data.get("title", "Bar Plot"))
        ax.set_xlabel(data.get("xlabel", ""))
        ax.set_ylabel(data.get("ylabel", ""))
        ax.grid(True, axis="y")
