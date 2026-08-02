"""Chart check edge — conditional routing based on chart_requested flag.

Routes to the visualization node if a chart was requested by the planner,
otherwise skips directly to the evaluator.
"""

from typing import Literal

from analyst.schemas.state import GraphState


def chart_check(state: GraphState) -> Literal["visualization", "evaluator"]:
    """Route to visualization or evaluator based on chart_requested flag."""
    if state.get("chart_requested", False):
        return "visualization"
    return "evaluator"
