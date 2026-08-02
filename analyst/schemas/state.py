"""GraphState — central state schema for the multi-agent analysis pipeline.

Every node reads from and writes partial updates to this TypedDict.
Fields with ``Annotated[..., add]`` use reducers so parallel fan-in works.
"""

from operator import add
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """Shared state flowing through the LangGraph pipeline."""

    # User Input
    user_query: str
    sanitized_message: str

    # Intent Classification
    intent: str                             # "chat" | "task" | "followup"
    intent_confidence: float
    intent_reason: str

    # Conversation Context
    messages: Annotated[list, add_messages]  # LangChain message history
    topic: str
    turn_state: str                         # "new" | "continuing"

    # Planner
    plan: list[dict]                        # ordered steps from planner
    current_step_index: int

    # Parallel Agent Results (fan-in via reducer)
    tool_results: Annotated[list[dict], add]

    # Merged Dataset
    merged_data: dict | None             # combined dataset after merge

    # Analysis
    analysis_results: dict | None        # EDA / transform output
    insights: str | None                 # LLM-generated narrative

    # Visualization
    chart_requested: bool
    chart_result: dict | None            # build_chart output

    # Evaluation
    evaluation: dict | None              # evaluator verdict

    # Output
    final_answer: str

    # DB Schema (for SQL generation)
    schema: dict | None

    # File Context
    uploaded_files: list[dict]              # [{file_id, filename, path, content_type}]

    # Error Tracking
    execution_errors: Annotated[list[str], add]
