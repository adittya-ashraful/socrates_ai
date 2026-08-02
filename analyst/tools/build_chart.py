"""Pure chart-building function — no graph dependency.

Generates matplotlib charts, saves to disk, and returns
both file path and base64-encoded PNG.
"""

import base64
import io
import os
import uuid

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from analyst.config import CHART_DIR


def build_chart(
    df: pd.DataFrame,
    chart_type: str,
    x: str,
    y: str,
    title: str = "",
    color_by: str | None = None,
) -> dict:
    """Build a chart and return path + base64 PNG.

    Args:
        df: Source data
        chart_type: "bar" | "line" | "scatter" | "hist" | "heatmap"
        x: Column for x-axis
        y: Column for y-axis
        title: Chart title
        color_by: Optional grouping column (for heatmap pivot)

    Returns:
        dict with chart_path, chart_b64, title, type
    """
    fig, ax = plt.subplots(figsize=(8, 4))

    if y in df.columns:
        df[y] = pd.to_numeric(df[y], errors='coerce')

    if chart_type == "bar":
        df.plot.bar(x=x, y=y, ax=ax, legend=bool(color_by))
    elif chart_type == "line":
        df.plot.line(x=x, y=y, ax=ax)
    elif chart_type == "scatter":
        df.plot.scatter(x=x, y=y, ax=ax)
    elif chart_type == "hist":
        df[y].plot.hist(bins=20, ax=ax)
    elif chart_type == "heatmap":
        import seaborn as sns
        pivot = df.pivot(index=x, columns=color_by, values=y)
        sns.heatmap(pivot, ax=ax)

    ax.set_title(title)
    plt.tight_layout()

    # Save file
    os.makedirs(CHART_DIR, exist_ok=True)
    filename = os.path.join(CHART_DIR, f"{uuid.uuid4().hex}.png")
    fig.savefig(filename, dpi=120, bbox_inches="tight")

    # Base64
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    b64 = base64.b64encode(buf.getvalue()).decode()
    plt.close(fig)

    return {
        "chart_path": filename,
        "chart_b64": b64,
        "title": title,
        "type": chart_type,
    }
