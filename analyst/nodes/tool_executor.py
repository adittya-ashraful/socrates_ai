"""Tool Executor node — executes sql, search, and file tools concurrently.

Replaces the parallel fan-out pattern to avoid LangGraph parallel fan-in execution bugs
where multiple nodes pointing to the same sink cause the sink to execute multiple times.
"""

import concurrent.futures

from analyst.nodes.file_executor import file_executor_node
from analyst.nodes.search_tool import search_tool_node
from analyst.nodes.sql_tool import sql_tool_node
from analyst.schemas.state import GraphState


def tool_executor_node(state: GraphState) -> dict:
    """Execute all required tool steps from the plan concurrently.
    
    Returns results that merge into ``tool_results``.
    """
    plan = state.get("plan", [])
    if not plan:
        return {}

    tool_types = {step.get("tool") for step in plan}
    
    results = []
    errors = []
    
    def run_sql():
        if "sql" in tool_types:
            return sql_tool_node(state)
        return {}
        
    def run_search():
        if "search" in tool_types:
            return search_tool_node(state)
        return {}
        
    def run_file():
        if "file" in tool_types:
            return file_executor_node(state)
        return {}
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(run_sql),
            executor.submit(run_search),
            executor.submit(run_file),
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if res.get("tool_results"):
                    results.extend(res["tool_results"])
                if res.get("execution_errors"):
                    errors.extend(res["execution_errors"])
            except Exception as e:
                errors.append(f"Tool executor internal error: {e}")
                
    return {
        "tool_results": results,
        "execution_errors": errors
    }
