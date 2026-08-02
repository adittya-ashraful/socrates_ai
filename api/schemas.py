"""Pydantic request / response models for the Socrates AI API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Requests 

class QueryRequest(BaseModel):
    """Body for POST /api/query and /api/stream."""

    query: str = Field(..., min_length=1, max_length=8000, description="User question")
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread ID. Omit to start a new thread.",
    )


class ChatRequest(BaseModel):
    """Body for POST /api/chat and /api/chat/stream."""

    message: str = Field(..., min_length=1, max_length=8000, description="User message")
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread ID. Omit to start a new conversation.",
    )
    file_ids: list[str] | None = Field(
        default=None,
        description="List of file IDs (from /api/upload) to include as context.",
    )


# Responses 

class ChartInfo(BaseModel):
    """Chart metadata returned when a visualization was generated."""

    title: str = ""
    type: str = ""
    path: str | None = None
    b64: str | None = None


class QueryResponse(BaseModel):
    """Structured response from POST /api/query."""

    answer: str
    thread_id: str
    intent: str = ""
    chart: ChartInfo | None = None
    evaluation: dict | None = None
    errors: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Structured response from POST /api/chat."""

    message: str
    thread_id: str
    intent: str = ""
    chart: ChartInfo | None = None
    files_used: list[str] = Field(default_factory=list)
    metadata: dict | None = None


class UploadResponse(BaseModel):
    """Response from POST /api/upload."""

    file_id: str
    filename: str
    size_bytes: int
    content_type: str


class ThreadInfo(BaseModel):
    """Thread metadata for GET /api/threads."""

    thread_id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_message: str | None = None


class StreamEvent(BaseModel):
    """A single SSE event sent during POST /api/stream."""

    event: str = Field(
        ..., description="Event type: node_start | node_end | result | error"
    )
    node: str | None = None
    data: dict | None = None


class HealthResponse(BaseModel):
    """Response for GET /api/health."""

    status: str = "ok"
