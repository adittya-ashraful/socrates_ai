"""Canonical Artifact schema.

Every tool writes output into this shape. The tool_orchestrator
validates it before the next node reads it.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Artifact(BaseModel):
    """Standardised output from every tool execution step."""

    step_id: str = Field(..., description="Unique ID matching the plan step")
    tool: Literal["sql", "pandas_eda", "data_pipeline", "viz", "chat"] = Field(
        ..., description="Which tool produced this artifact"
    )
    status: Literal["ok", "error"] = Field(
        ..., description="Whether the tool succeeded"
    )
    data: Any | None = Field(
        default=None,
        description="DataFrame records, stats dict, chart meta, etc.",
    )
    error: str | None = Field(
        default=None, description="Error message if status == 'error'"
    )
    shape: dict | None = Field(
        default=None,
        description='{"rows": int, "columns": list[str]} for tabular outputs',
    )
    chart_path: str | None = Field(
        default=None, description="Absolute path to saved figure"
    )
    chart_b64: str | None = Field(
        default=None, description="Base64 PNG for inline delivery"
    )
    sql_query: str | None = Field(
        default=None, description="The actual SQL executed (for audit)"
    )
    metadata: dict = Field(
        default_factory=dict, description="Arbitrary extra metadata"
    )
    artifact_uri: str | None = None