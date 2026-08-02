"""Merge Dataset node — combines outputs from all parallel tools.

Takes ``tool_results`` (populated by SQL, Search, and File tools)
and produces a unified ``merged_data`` dict for the analysis pipeline.
"""

import pandas as pd

from analyst.schemas.state import GraphState
from analyst.utils.sanitize import sanitize_numpy


def merge_dataset_node(state: GraphState) -> dict:
    """Merge all tool results into a single dataset.

    Strategy:
    - SQL & File tools produce tabular data → concat into one DataFrame
    - Search tools produce text data → kept as supplementary context
    - Everything is combined into ``merged_data``
    """
    tool_results = state.get("tool_results", [])

    tabular_frames: list[pd.DataFrame] = []
    search_context: list[dict] = []
    errors = []

    for result in tool_results:
        artifact = result.get("artifact", {})
        tool_type = result.get("tool", "unknown")

        if artifact.get("status") != "ok":
            continue

        data = artifact.get("data")
        if data is None:
            continue

        if tool_type in ("sql", "file"):
            # Tabular data — convert records to DataFrame
            if isinstance(data, list) and len(data) > 0:
                try:
                    df = pd.DataFrame(data)
                    tabular_frames.append(df)
                except Exception as e:
                    errors.append(f"Merge error ({tool_type}): {e}")

        elif tool_type == "search":
            # Text data — keep as context
            if isinstance(data, list):
                search_context.extend(data)

    # Combine tabular data
    merged_records = []
    merged_columns = []
    merged_row_count = 0

    if tabular_frames:
        try:
            # Concat all frames (outer join to preserve all columns)
            combined = pd.concat(tabular_frames, ignore_index=True)
            merged_records = sanitize_numpy(
                combined.to_dict(orient="records")
            )
            merged_columns = list(combined.columns)
            merged_row_count = len(combined)
        except Exception as e:
            errors.append(f"DataFrame concat error: {e}")

    merged_data = {
        "records": merged_records,
        "columns": merged_columns,
        "row_count": merged_row_count,
        "search_context": search_context,
        "source_count": len(tool_results),
    }

    return {
        "merged_data": merged_data,
        "execution_errors": errors,
    }
