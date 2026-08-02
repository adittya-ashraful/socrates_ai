"""Search Agent node — retrieves external information via Tavily web search.

Used when the planner determines that required information is not available
in internal databases or files.
"""

import os

from analyst.schemas.state import GraphState

# Tavily search tool
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    _tavily_available = True
except ImportError:
    _tavily_available = False


def search_tool_node(state: GraphState) -> dict:
    """Execute web search steps from the plan.

    Uses Tavily search to find external information.
    Returns results that merge into ``tool_results``.
    """
    plan = state.get("plan", [])
    search_steps = [s for s in plan if s.get("tool") == "search"]

    results = []
    errors = []

    if not _tavily_available:
        for step in search_steps:
            errors.append(
                f"Search unavailable ({step.get('step_id', '?')}): "
                "langchain-community not installed"
            )
            results.append({
                "tool": "search",
                "step_id": step.get("step_id", "search_unknown"),
                "artifact": {
                    "step_id": step.get("step_id", "search_unknown"),
                    "tool": "chat",
                    "status": "error",
                    "error": "Tavily search not available",
                    "data": None,
                },
            })
        return {"tool_results": results, "execution_errors": errors}

    tavily_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_key:
        for step in search_steps:
            errors.append(f"Search ({step.get('step_id', '?')}): TAVILY_API_KEY not set")
            results.append({
                "tool": "search",
                "step_id": step.get("step_id", "search_unknown"),
                "artifact": {
                    "step_id": step.get("step_id", "search_unknown"),
                    "tool": "chat",
                    "status": "error",
                    "error": "TAVILY_API_KEY not configured",
                    "data": None,
                },
            })
        return {"tool_results": results, "execution_errors": errors}

    search_tool = TavilySearchResults(
        max_results=5,
        api_key=tavily_key,
    )

    for step in search_steps:
        params = step.get("params", {})
        step_id = step.get("step_id", "search_unknown")
        query = params.get("query", state.get("user_query", ""))

        try:
            search_results = search_tool.invoke(query)

            # Normalize results into a consistent format
            data = []
            for item in search_results:
                data.append({
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                })

            results.append({
                "tool": "search",
                "step_id": step_id,
                "artifact": {
                    "step_id": step_id,
                    "tool": "chat",
                    "status": "ok",
                    "data": data,
                    "metadata": {"query": query, "result_count": len(data)},
                },
            })
        except Exception as e:
            errors.append(f"Search error ({step_id}): {e}")
            results.append({
                "tool": "search",
                "step_id": step_id,
                "artifact": {
                    "step_id": step_id,
                    "tool": "chat",
                    "status": "error",
                    "error": str(e),
                    "data": None,
                },
            })

    return {
        "tool_results": results,
        "execution_errors": errors,
    }
