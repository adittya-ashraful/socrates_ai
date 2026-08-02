from typing import Literal

from analyst.schemas.state import GraphState

RouteDest= Literal["direct_answer","planner"]
def route_by_intent(state: GraphState) -> str:
    """Conditional edge: decide where to go based on intent + confidence.
    - chat      -> direct_answer
    - task      -> planner
    - followup  -> planner
    """
    
    intent = state["intent"]

    if intent == "chat":
        return "direct_answer"

    if intent in {"task", "followup"}:
        return "planner"

    raise ValueError(f"Unknown intent: {intent}")