import os
from pathlib import Path
from typing import Dict


class DashboardVisualizer:
    """
    Simple HTML stitcher for combining multiple feature reports into
    a single dashboard entry point.
    """

    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def build_overview(self, sections: Dict[str, str], filename: str = "dashboard.html") -> str:
        """
        sections: { "AEB": "path/to/aeb.html", "FCW": "path/to/fcw.html", ... }
        Returns the path to the generated dashboard file.
        """
        if not sections:
            raise ValueError("sections must be a non-empty mapping of name -> html path.")

        target = Path(self.out_dir) / filename
        cards = []
        for name, path in sections.items():
            rel = os.path.relpath(path, start=self.out_dir)
            cards.append(
                f"""<section class="card">
  <header><h2>{name}</h2></header>
  <p><a href="{rel}">Open standalone report</a></p>
  <iframe src="{rel}" loading="lazy"></iframe>
</section>"""
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>KPI Dashboard</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 24px;
      background: #f6f7fb;
      color: #222;
    }}
    h1 {{ margin-bottom: 12px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.08);
      padding: 12px;
      display: flex;
      flex-direction: column;
      min-height: 240px;
    }}
    .card iframe {{
      border: 1px solid #e1e1e1;
      border-radius: 6px;
      min-height: 240px;
      width: 100%;
      flex: 1;
    }}
    .card a {{
      color: #0063c8;
      text-decoration: none;
    }}
    .card a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>KPI Dashboard</h1>
  <div class="grid">
    {"".join(cards)}
  </div>
</body>
</html>
"""
        target.write_text(html, encoding="utf-8")
        print(f"💾 Dashboard saved → {target}")
        return str(target)
