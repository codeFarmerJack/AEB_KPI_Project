from utils.viz.dashboard import Dashboard

# Example data
x = [0, 1, 2, 3, 4]
y = [10, 14, 12, 18, 22]

# 1) Create a dashboard with 1 row, 1 column
dashboard = Dashboard(rows=1, cols=1)

# 2) Add a plot
dashboard.add(
    row=0,
    col=0,
    plot="xy",               # key from registry.py
    data={
        "x": x,
        "y": y,
        "xlabel": "Time (s)",
        "ylabel": "Value",
        "title": "My First XY Plot"
    }
)

# 3) Render & show
fig = dashboard.render()
fig.show()
