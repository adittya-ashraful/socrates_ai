"""Planner node — decomposes complex queries into tool-executable steps.

Receives a ``task`` or ``followup`` intent and produces a structured plan
that tells the fan-out edge which parallel tools to invoke and with what params.
"""

import json

from analyst.schemas.state import GraphState
from analyst.utils.db import get_db_schema
from analyst.utils.helpers import extract_json
from analyst.utils.llm import get_llm

PLANNER_PROMPT = """\
You are the planning module of an AI data analyst system.

Given the user's query, database schema, uploaded files, and conversation context,
produce a JSON execution plan.

Each step should specify which tool to use and the parameters it needs.

Available tools:
- "sql"    — query a SQL database.  Params: {{"intent_hint": str, "filters": dict}}
- "search" — web search for external info.  Params: {{"query": str}}
- "file"   — load a local file (CSV/Parquet).  Params: {{"file_path": str}}

Also decide:
- "chart_requested": true/false — whether a visualization should be generated

Rules:
- Include only the tools actually needed for the query.
- Each step must have a unique "step_id" (e.g. "s1", "s2", ...).
- Be precise with SQL intent hints — reference actual table/column names from the schema.
- If the query can be answered with a single SQL query, use only one sql step.
- Set status to "pending" for all steps.
- If uploaded files are available and the user's query relates to analyzing data,
  include a "file" step for each relevant uploaded file using its exact "path" value.
- Prefer uploaded files over SQL when the user explicitly mentions uploaded/attached data.

Database schema:
{schema}

Uploaded files:
{uploaded_files}

User query:
{query}

Previous context:
{context}

Respond ONLY with valid JSON, no markdown:
{{
    "steps": [
        {{"step_id": "s1", "tool": "<tool>", "params": {{...}}, "status": "pending"}}
    ],
    "chart_requested": true/false,
    "reasoning": "<one sentence explaining plan>"
}}
"""


def planner_node(state: GraphState) -> dict:
    """Decompose user query into an execution plan with parallel tool steps."""
    llm = get_llm(temperature=0.0)

    # Auto-introspect DB schema
    try:
        db_schema = get_db_schema()
    except Exception:
        db_schema = state.get("schema", {})

    # Build context from previous messages
    context_parts = []
    if state.get("insights"):
        context_parts.append(f"Previous insights: {state['insights']}")
    if state.get("analysis_results"):
        context_parts.append("Previous analysis results available")
    context = "\n".join(context_parts) if context_parts else "None"

    # Build uploaded files info for the prompt
    uploaded_files = state.get("uploaded_files", [])
    if uploaded_files:
        file_lines = [
            f"- filename: {f.get('filename', 'unknown')}, "
            f"path: {f.get('path', 'unknown')}, "
            f"type: {f.get('content_type', 'unknown')}"
            for f in uploaded_files
        ]
        uploaded_files_str = "\n".join(file_lines)
    else:
        uploaded_files_str = "None"

    prompt = PLANNER_PROMPT.format(
        schema=json.dumps(db_schema, indent=2, default=str),
        query=state.get("sanitized_message", state.get("user_query", "")),
        context=context,
        uploaded_files=uploaded_files_str,
    )

    response = llm.invoke(prompt)
    parsed = json.loads(extract_json(response.content))

    plan = parsed.get("steps", [])
    chart_requested = parsed.get("chart_requested", False)

    # Ensure each step has a unique step_id
    for i, step in enumerate(plan):
        if "step_id" not in step:
            step["step_id"] = f"s{i + 1}"
        step.setdefault("status", "pending")

    return {
        "plan": plan,
        "chart_requested": chart_requested,
        "current_step_index": 0,
        "schema": db_schema,
    }
