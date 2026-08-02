"""Planner fan-out edge — dispatches plan steps to parallel tools via Send().

After the planner produces a plan, this conditional edge inspects the steps
and fans out to the appropriate tool nodes in parallel using LangGraph's
Send API. All tools write to ``tool_results`` which uses an ``add`` reducer,
so results accumulate correctly.
"""



from analyst.schemas.state import GraphState


def fan_out_to_tools(state: GraphState) -> str:
    """Inspect the plan and route to the tool executor if tools are needed.

    If the plan is empty or has no recognized tools,
    routes directly to merge_dataset so the pipeline can gracefully degrade.
    """
    plan = state.get("plan", [])

    if not plan:
        # No plan steps → skip tools, go straight to merge
        return "merge_dataset"

    # Determine which tools are needed
    tool_types = {step.get("tool") for step in plan}
    
    if any(t in {"sql", "search", "file"} for t in tool_types):
        return "tool_executor"
        
    return "merge_dataset"
