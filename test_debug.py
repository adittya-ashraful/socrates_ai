import asyncio

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict


class State(TypedDict):
    a: int

def node_a(state):
    return {"a": state["a"] + 1}

def node_b(state):
    return {"a": state["a"] + 1}

builder = StateGraph(State)
builder.add_node("node_a", node_a)
builder.add_node("node_b", node_b)
builder.add_edge(START, "node_a")
builder.add_edge("node_a", "node_b")
builder.add_edge("node_b", END)

graph = builder.compile()

async def main():
    async for stream_mode, payload in graph.astream({"a": 1}, stream_mode=["updates", "debug"]):
        if stream_mode == "debug":
            print("DEBUG:", payload.get("type"), payload.get("payload", {}).get("name") if hasattr(payload, "get") and isinstance(payload.get("payload"), dict) else payload.get("step") if hasattr(payload, "get") else payload)

asyncio.run(main())
