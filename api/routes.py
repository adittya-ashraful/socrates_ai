"""API routes for Socrates AI.

Endpoints:
    POST /api/chat            — conversational chat (returns full result)
    POST /api/chat/stream     — conversational chat with SSE streaming
    POST /api/upload          — upload a file (persistent storage + PostgreSQL)
    GET  /api/threads         — list conversation threads
    GET  /api/threads/{id}/history — get message history for a thread
    DELETE /api/threads/{id}  — delete a conversation thread
    POST /api/query           — synchronous query (legacy, returns full result)
    POST /api/stream          — SSE streaming (legacy, node-by-node progress)
    GET  /api/health          — health check
"""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.db import (
    create_thread,
    delete_thread,
    get_thread,
    link_file_to_thread,
    list_threads,
    update_thread,
)
from api.schemas import (
    ChartInfo,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ThreadInfo,
    UploadResponse,
)

router = APIRouter(prefix="/api", tags=["analysis"])


# Helpers

def _build_initial_state(query: str, uploaded_files: list[dict] | None = None) -> dict:
    """Build the initial GraphState dict expected by the pipeline."""
    return {
        "user_query": query,
        "sanitized_message": query,
        "messages": [],
        "topic": "none",
        "turn_state": "new",
        "tool_results": [],
        "execution_errors": [],
        "chart_requested": False,
        "uploaded_files": uploaded_files or [],
    }


def _build_chat_state(
    message: str,
    uploaded_files: list[dict] | None = None,
) -> dict:
    """Build graph state for the chat endpoint — includes a HumanMessage."""
    return {
        "user_query": message,
        "sanitized_message": message,
        "messages": [HumanMessage(
            content=message, 
            additional_kwargs={"files": uploaded_files} if uploaded_files else {}
        )],
        "topic": "none",
        "turn_state": "new",
        "tool_results": [],
        "execution_errors": [],
        "chart_requested": False,
        "uploaded_files": uploaded_files or [],
    }


def _extract_response(result: dict, thread_id: str) -> QueryResponse:
    """Convert raw graph output to the API response model."""
    chart = None
    chart_raw = result.get("chart_result")
    if chart_raw:
        chart = ChartInfo(
            title=chart_raw.get("title", ""),
            type=chart_raw.get("type", ""),
            path=chart_raw.get("chart_path"),
        )

    return QueryResponse(
        answer=result.get("final_answer", "No answer produced."),
        thread_id=thread_id,
        intent=result.get("intent", ""),
        chart=chart,
        evaluation=result.get("evaluation"),
        errors=result.get("execution_errors", []),
    )


def _extract_chat_response(
    result: dict,
    thread_id: str,
    files_used: list[str],
) -> ChatResponse:
    """Convert raw graph output to a ChatResponse."""
    chart = None
    chart_raw = result.get("chart_result")
    if chart_raw:
        chart = ChartInfo(
            title=chart_raw.get("title", ""),
            type=chart_raw.get("type", ""),
            path=chart_raw.get("chart_path"),
            b64=chart_raw.get("chart_b64"),
        )

    metadata = {}
    if result.get("evaluation"):
        metadata["evaluation"] = result["evaluation"]
    if result.get("execution_errors"):
        metadata["errors"] = result["execution_errors"]

    return ChatResponse(
        message=result.get("final_answer", "No answer produced."),
        thread_id=thread_id,
        intent=result.get("intent", ""),
        chart=chart,
        files_used=files_used,
        metadata=metadata or None,
    )


async def _resolve_files(request: Request, file_ids: list[str] | None) -> tuple[list[dict], list[str]]:
    """Look up file metadata for the given IDs.

    Returns:
        (uploaded_files for graph state, list of file_id strings used)
    """
    if not file_ids:
        return [], []

    file_manager = request.app.state.file_manager
    file_metas = await file_manager.get_many(file_ids)

    uploaded_files = [
        {
            "file_id": f["file_id"],
            "filename": f["filename"],
            "path": f["file_path"],
            "content_type": f["content_type"],
        }
        for f in file_metas
    ]
    used_ids = [f["file_id"] for f in file_metas]
    return uploaded_files, used_ids


# POST /api/chat — Main conversational endpoint

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    """Send a message and receive the agent's full response.

    Supports multi-turn conversation via ``thread_id`` and file context
    via ``file_ids`` (returned from ``POST /api/upload``).
    """
    graph = request.app.state.graph
    pool = request.app.state.pool
    thread_id = body.thread_id or str(uuid.uuid4())

    # Ensure thread exists in DB
    await create_thread(pool, thread_id, title=body.message[:100])

    # Resolve attached files
    uploaded_files, files_used = await _resolve_files(request, body.file_ids)

    # Link files to this thread
    for fid in files_used:
        await link_file_to_thread(pool, fid, thread_id)

    # Build state and invoke
    initial_state = _build_chat_state(body.message, uploaded_files)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await asyncio.to_thread(graph.invoke, initial_state, config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Update thread with last message
    answer = result.get("final_answer", "No answer produced.")
    await update_thread(pool, thread_id, last_message=answer[:500])

    return _extract_chat_response(result, thread_id, files_used)


# POST /api/chat/stream — SSE streaming chat

@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, request: Request):
    """Stream node-by-node progress as Server-Sent Events.

    Event types:
        node_start  — a node is about to execute
        node_end    — a node finished (includes output keys)
        result      — final ChatResponse payload
        error       — something went wrong
    """
    graph = request.app.state.graph
    pool = request.app.state.pool
    thread_id = body.thread_id or str(uuid.uuid4())

    await create_thread(pool, thread_id, title=body.message[:100])

    uploaded_files, files_used = await _resolve_files(request, body.file_ids)
    for fid in files_used:
        await link_file_to_thread(pool, fid, thread_id)

    initial_state = _build_chat_state(body.message, uploaded_files)
    config = {"configurable": {"thread_id": thread_id}}

    async def _event_generator():
        """Yield SSE-formatted strings."""
        try:
            stream_iter = graph.astream(initial_state, config, stream_mode=["updates", "debug"])
            
            NODE_STATUS_MAP = {
                "intent_classifier": "thinking",
                "planner": "thinking",
                "file_executor": "loading_context",
                "sql_tool": "loading_context",
                "merge_dataset": "loading_context",
                "search_tool": "searching",
                "tool_executor": "searching",
                "analysis": "analyzing",
                "visualization": "analyzing",
                "evaluator": "analyzing",
                "final_response": "generating",
                "direct_answer": "generating",
            }
            
            async for stream_mode, payload in stream_iter:
                if stream_mode == "debug":
                    event_type = payload.get("type")
                    if event_type == "task": # LangGraph 1.1.9 task starts
                        node_name = payload.get("payload", {}).get("name")
                        status = NODE_STATUS_MAP.get(node_name)
                        if status:
                            event = {"event": "node_start", "node": status, "data": None}
                            yield f"event: node_start\ndata: {json.dumps(event)}\n\n"
                    elif event_type == "task_result": # LangGraph 1.1.9 task ends
                        node_name = payload.get("payload", {}).get("name")
                        status = NODE_STATUS_MAP.get(node_name)
                        if status:
                            event = {"event": "node_end", "node": status, "data": {"output_keys": []}}
                            yield f"event: node_end\ndata: {json.dumps(event)}\n\n"
                
                elif stream_mode == "updates":
                    # Emit tokens and other specific updates
                    for node_name, state_patch in payload.items():
                        if isinstance(state_patch, dict):
                            if "insights" in state_patch and node_name == "analysis":
                                event = {
                                    "event": "token",
                                    "node": node_name,
                                    "data": state_patch["insights"] + "\n\n",
                                }
                                yield f"event: token\ndata: {json.dumps(event)}\n\n"
                                
                            if "final_answer" in state_patch and node_name in ("final_response", "direct_answer"):
                                event = {
                                    "event": "token",
                                    "node": node_name,
                                    "data": state_patch["final_answer"],
                                }
                                yield f"event: token\ndata: {json.dumps(event)}\n\n"

            # Retrieve final state after stream completes
            final_state = await graph.aget_state(config)
            final_result = final_state.values if final_state else {}

            # Update thread
            answer = final_result.get("final_answer", "")
            await update_thread(pool, thread_id, last_message=answer[:500])

            response = _extract_chat_response(final_result, thread_id, files_used)
            event = {
                "event": "result",
                "node": None,
                "data": response.model_dump(),
            }
            yield f"event: result\ndata: {json.dumps(event, default=str)}\n\n"

        except Exception as exc:
            event = {
                "event": "error",
                "node": None,
                "data": {"detail": str(exc)},
            }
            yield f"event: error\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# POST /api/upload — File upload (persistent)

@router.post("/upload", response_model=UploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload a file. Returns a ``file_id`` to reference in chat messages."""
    file_manager = request.app.state.file_manager

    try:
        meta = await file_manager.save(file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return UploadResponse(
        file_id=meta["file_id"],
        filename=meta["filename"],
        size_bytes=meta["size_bytes"],
        content_type=meta["content_type"],
    )


# Thread Management

@router.get("/threads", response_model=list[ThreadInfo])
async def get_threads(request: Request, limit: int = 50, offset: int = 0):
    """List conversation threads, ordered by most recently active."""
    pool = request.app.state.pool
    threads = await list_threads(pool, limit=limit, offset=offset)
    return [ThreadInfo(**t) for t in threads]


@router.get("/threads/{thread_id}", response_model=ThreadInfo)
async def get_thread_info(thread_id: str, request: Request):
    """Get metadata for a single thread."""
    pool = request.app.state.pool
    thread = await get_thread(pool, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadInfo(**thread)


@router.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, request: Request):
    """Get the full message history for a thread from the checkpointer.

    Returns a list of messages in chronological order.
    """
    graph = request.app.state.graph
    pool = request.app.state.pool

    # Verify thread exists
    thread = await get_thread(pool, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = await asyncio.to_thread(graph.get_state, config)
    except Exception:
        return {"thread_id": thread_id, "messages": []}

    if state is None or state.values is None:
        return {"thread_id": thread_id, "messages": []}

    raw_messages = state.values.get("messages", [])
    messages = []
    for msg in raw_messages:
        files = msg.additional_kwargs.get("files") if hasattr(msg, "additional_kwargs") else None
        m_dict = {
            "role": "human" if isinstance(msg, HumanMessage) else "ai",
            "content": msg.content,
        }
        if files:
            m_dict["files"] = files
        messages.append(m_dict)

    return {"thread_id": thread_id, "messages": messages}


@router.delete("/threads/{thread_id}")
async def remove_thread(thread_id: str, request: Request):
    """Delete a conversation thread and its associated file metadata."""
    pool = request.app.state.pool
    deleted = await delete_thread(pool, thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"status": "deleted", "thread_id": thread_id}


@router.get("/threads/{thread_id}/files")
async def get_thread_files(thread_id: str, request: Request):
    """List all files associated with a thread."""
    pool = request.app.state.pool
    file_manager = request.app.state.file_manager

    thread = await get_thread(pool, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    files = await file_manager.list_for_thread(thread_id)
    return {"thread_id": thread_id, "files": files}


# Legacy Endpoints (kept for backward compatibility)

@router.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest, request: Request):
    """Run the full analysis pipeline and return the result."""
    graph = request.app.state.graph
    thread_id = body.thread_id or str(uuid.uuid4())

    initial_state = _build_initial_state(body.query)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await asyncio.to_thread(graph.invoke, initial_state, config)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return _extract_response(result, thread_id)


@router.post("/stream")
async def stream(body: QueryRequest, request: Request):
    """Stream node-by-node progress as Server-Sent Events (SSE).

    Event types:
        node_start  — a node is about to execute
        node_end    — a node finished (includes its output keys)
        result      — final result payload
        error       — something went wrong
    """
    graph = request.app.state.graph
    thread_id = body.thread_id or str(uuid.uuid4())

    initial_state = _build_initial_state(body.query)
    config = {"configurable": {"thread_id": thread_id}}

    async def _event_generator():
        """Yield SSE-formatted strings."""
        try:
            # graph.stream() yields (node_name, state_update) tuples
            stream_iter = graph.stream(initial_state, config, stream_mode="updates")

            final_result: dict = {}

            for update in await asyncio.to_thread(list, stream_iter):
                # Each update is {node_name: state_patch}
                for node_name, state_patch in update.items():
                    # Emit node_start
                    event = {
                        "event": "node_start",
                        "node": node_name,
                        "data": None,
                    }
                    yield f"event: node_start\ndata: {json.dumps(event)}\n\n"

                    # Gather output keys (skip large data blobs)
                    output_keys = list(state_patch.keys()) if isinstance(state_patch, dict) else []

                    # Emit node_end
                    event = {
                        "event": "node_end",
                        "node": node_name,
                        "data": {"output_keys": output_keys},
                    }
                    yield f"event: node_end\ndata: {json.dumps(event)}\n\n"

                    # Track final state updates
                    if isinstance(state_patch, dict):
                        final_result.update(state_patch)

            # Emit the final result
            response = _extract_response(final_result, thread_id)
            event = {
                "event": "result",
                "node": None,
                "data": response.model_dump(),
            }
            yield f"event: result\ndata: {json.dumps(event, default=str)}\n\n"

        except Exception as exc:
            event = {
                "event": "error",
                "node": None,
                "data": {"detail": str(exc)},
            }
            yield f"event: error\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


#  GET /api/health

@router.get("/health", response_model=HealthResponse)
async def health():
    """Simple health check."""
    return HealthResponse(status="ok")
