from ..base_plot import BasePlot


class PiePlotter(BasePlot):
    """
    Pie chart plotter.

    Expected data dict:
    {
        "labels": [...],              # categories
        "values": [...],              # corresponding values
        "title": "Optional chart title",
        "autopct": "%.1f%%",          # optional formatting of percentages
        "startangle": 90,             # optional rotation
        "explode": [0, 0.1, ...],     # optional explode list same length as values
    }
    """

    name = "pie"

    def draw(self, ax, data):
        labels = data["labels"]
        values = data["values"]

        autopct = data.get("autopct", "%.1f%%")
        startangle = data.get("startangle", 90)
        explode = data.get("explode", None)

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct=autopct,
            startangle=startangle,
            explode=explode,
        )

        ax.set_title(data.get("title", "Pie Chart"))
        ax.axis("equal")  # keep the pie circular
