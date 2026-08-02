"""Evaluator node — reviews and validates pipeline output.

Ensures quality, factual consistency, and completeness of
insights and visualizations before final delivery.
"""

import json

from analyst.schemas.state import GraphState
from analyst.utils.helpers import extract_json
from analyst.utils.llm import get_llm

EVALUATOR_PROMPT = """\
You are a quality evaluator for an AI data analyst system.

Review the analysis output and determine if it meets quality standards.

User's original question:
{query}

Insights generated:
{insights}

Chart generated: {has_chart}
Errors encountered: {errors}

Data summary:
- Sources used: {source_count}
- Rows analyzed: {row_count}

Evaluate on these criteria:
1. Relevance — Does the output answer the user's question?
2. Accuracy — Are the claims supported by the data?
3. Completeness — Is anything missing?
4. Clarity — Is the response clear and well-structured?

Respond ONLY with valid JSON:
{{
    "verdict": "pass" | "needs_improvement",
    "score": <0.0-1.0>,
    "feedback": "<specific feedback>",
    "suggestions": "<what to improve, or 'none' if passing>"
}}
"""


def evaluator_node(state: GraphState) -> dict:
    """Evaluate the quality of insights and visualization.

    Returns an evaluation verdict that the final_response node uses
    to decide whether to include caveats or improvement notes.
    """
    llm = get_llm(temperature=0.0)

    merged_data = state.get("merged_data", {})
    errors = state.get("execution_errors", [])

    prompt = EVALUATOR_PROMPT.format(
        query=state.get("user_query", ""),
        insights=state.get("insights", "No insights generated")[:3000],
        has_chart="Yes" if state.get("chart_result") else "No",
        errors=json.dumps(errors[-5:]) if errors else "None",
        source_count=merged_data.get("source_count", 0),
        row_count=merged_data.get("row_count", 0),
    )

    try:
        response = llm.invoke(prompt)
        evaluation = json.loads(extract_json(response.content))
    except Exception as e:
        evaluation = {
            "verdict": "pass",
            "score": 0.5,
            "feedback": f"Evaluation failed: {e}",
            "suggestions": "none",
        }

    return {
        "evaluation": evaluation,
    }
