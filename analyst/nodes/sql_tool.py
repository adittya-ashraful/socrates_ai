"""SQL Tool node — generates and executes SQL, returns result as tool_results.

Designed for the fan-out/fan-in pattern: receives task params via Send(),
returns results that merge into the shared ``tool_results`` list.
"""

from analyst.schemas.artifacts import Artifact
from analyst.schemas.state import GraphState
from analyst.tools.exe_sql import execute_sql
from analyst.tools.gen_sql import generate_sql


def sql_tool_node(state: GraphState) -> dict:
    """Execute a SQL operation from the plan and return as tool_results.

    Reads the plan step assigned to this tool, generates SQL if needed,
    executes it, and returns the result for merging downstream.
    """
    # Find the sql step(s) from the plan
    plan = state.get("plan", [])
    sql_steps = [s for s in plan if s.get("tool") == "sql"]

    results = []
    errors = []

    for step in sql_steps:
        params = step.get("params", {})
        step_id = step.get("step_id", "sql_unknown")

        # Generate SQL if not pre-supplied
        query = params.get("query") or generate_sql(
            intent=params.get("intent_hint", ""),
            schema=state.get("schema", {}),
            filters=params.get("filters", {}),
        )

        try:
            result = execute_sql(query, params.get("engine", "default"))
            artifact = Artifact(
                step_id=step_id,
                tool="sql",
                status="ok",
                data=result["records"],
                shape={"rows": result["row_count"], "columns": result["columns"]},
                sql_query=query,
            )
        except Exception as e:
            artifact = Artifact(
                step_id=step_id,
                tool="sql",
                status="error",
                error=str(e),
                sql_query=query,
            )
            errors.append(f"SQL error ({step_id}): {e}")

        results.append({
            "tool": "sql",
            "step_id": step_id,
            "artifact": artifact.model_dump(),
        })

    return {
        "tool_results": results,
        "execution_errors": errors,
    }
