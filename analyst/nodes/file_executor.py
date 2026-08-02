"""File Tool (Data Connector) node — loads data from files.

Handles CSV and Parquet files using the existing ``load_dataset`` tool.
Future extensions: API connectors, cloud storage, etc.
"""

from analyst.schemas.state import GraphState
from analyst.tools.load_dataset import load_dataset
from analyst.utils.sanitize import sanitize_numpy


def file_executor_node(state: GraphState) -> dict:
    """Execute file-loading steps from the plan.

    Loads CSV/Parquet files and returns data as ``tool_results``.
    """
    plan = state.get("plan", [])
    file_steps = [s for s in plan if s.get("tool") == "file"]

    results = []
    errors = []

    for step in file_steps:
        params = step.get("params", {})
        step_id = step.get("step_id", "file_unknown")
        file_path = params.get("file_path", "")

        if not file_path:
            errors.append(f"File tool ({step_id}): no file_path provided")
            results.append({
                "tool": "file",
                "step_id": step_id,
                "artifact": {
                    "step_id": step_id,
                    "tool": "data_pipeline",
                    "status": "error",
                    "error": "No file_path specified in plan params",
                    "data": None,
                },
            })
            continue

        try:
            df = load_dataset(file_path)
            records = sanitize_numpy(df.to_dict(orient="records"))
            columns = list(df.columns)

            results.append({
                "tool": "file",
                "step_id": step_id,
                "artifact": {
                    "step_id": step_id,
                    "tool": "data_pipeline",
                    "status": "ok",
                    "data": records,
                    "shape": {"rows": len(df), "columns": columns},
                    "metadata": {"file_path": file_path},
                },
            })
        except Exception as e:
            errors.append(f"File error ({step_id}): {e}")
            results.append({
                "tool": "file",
                "step_id": step_id,
                "artifact": {
                    "step_id": step_id,
                    "tool": "data_pipeline",
                    "status": "error",
                    "error": str(e),
                    "data": None,
                },
            })

    return {
        "tool_results": results,
        "execution_errors": errors,
    }