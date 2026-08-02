"""Visualization node — generates charts from analysis results.

Uses LLM to determine chart type and parameters, then calls
the ``build_chart`` tool to render the visualization.
"""

import json

import pandas as pd

from analyst.schemas.state import GraphState
from analyst.tools.build_chart import build_chart
from analyst.utils.helpers import extract_json
from analyst.utils.llm import get_llm

CHART_PLANNER_PROMPT = """\
You are a data visualization expert.

Based on the user's query and the analysis results, decide the best chart to create.

User query:
{query}

Data columns: {columns}
Data sample (first 3 rows): {sample}
Row count: {row_count}

Insights:
{insights}

Choose the best visualization and respond ONLY with valid JSON:
{{
    "chart_type": "bar" | "line" | "scatter" | "hist" | "heatmap",
    "x": "<column name for x-axis>",
    "y": "<column name for y-axis>",
    "title": "<descriptive chart title>",
    "color_by": "<optional grouping column or null>"
}}
"""


def visualization_node(state: GraphState) -> dict:
    """Generate a chart based on analysis results.

    Uses LLM to decide chart configuration, then calls build_chart.
    """
    merged_data = state.get("merged_data", {})
    records = merged_data.get("records", [])
    analysis_results = state.get("analysis_results", {})

    if not records:
        return {
            "chart_result": None,
            "execution_errors": ["No data available for visualization"],
        }

    try:
        df = pd.DataFrame(records)

        # Get sample for LLM context
        sample = df.head(3).to_dict(orient="records")

        # Ask LLM to plan the chart
        llm = get_llm(temperature=0.0)
        prompt = CHART_PLANNER_PROMPT.format(
            query=state.get("user_query", ""),
            columns=", ".join(df.columns.tolist()),
            sample=json.dumps(sample, indent=2, default=str)[:2000],
            row_count=len(df),
            insights=state.get("insights", "")[:1500],
        )

        response = llm.invoke(prompt)
        chart_config = json.loads(extract_json(response.content))

        # Validate columns exist
        x_col = chart_config.get("x", "")
        y_col = chart_config.get("y", "")

        if x_col not in df.columns or y_col not in df.columns:
            # Fallback: use first two columns
            cols = list(df.columns)
            x_col = cols[0] if len(cols) > 0 else ""
            y_col = cols[1] if len(cols) > 1 else cols[0]

        chart_result = build_chart(
            df=df,
            chart_type=chart_config.get("chart_type", "bar"),
            x=x_col,
            y=y_col,
            title=chart_config.get("title", "Analysis Chart"),
            color_by=chart_config.get("color_by"),
        )

        return {
            "chart_result": chart_result,
            "execution_errors": [],
        }

    except Exception as e:
        return {
            "chart_result": None,
            "execution_errors": [f"Visualization error: {e}"],
        }
