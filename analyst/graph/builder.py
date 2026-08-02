"""Graph builder — wires all nodes and edges into the LangGraph StateGraph.

Architecture flow:
    START → intent_classifier → [route_by_intent]
      ├─ "direct_answer" → final_response_simple → END
      └─ "planner" → planner → [fan_out_to_tools]
                                  ├─ sql_tool ──┐
                                  ├─ search_tool ┼→ merge_dataset → analysis → [chart_check]
                                  └─ file_executor ──┘                               ├─ visualization → evaluator
                                                                                  └─ evaluator
                                                                                       ↓
                                                                                 final_response → END
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from analyst.schemas.state import GraphState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver

# ── Nodes ─────────────────────────────────────────────────────────────────
from analyst.edges.chart_check import chart_check
from analyst.edges.planner_fan_out import fan_out_to_tools

# ── Edges ─────────────────────────────────────────────────────────────────
from analyst.edges.router import route_by_intent
from analyst.nodes.analysis import analysis_node
from analyst.nodes.direct_answer import direct_answer_node
from analyst.nodes.evaluator import evaluator_node
from analyst.nodes.final_response import final_response_node
from analyst.nodes.intent_classifier import intent_classifier_node
from analyst.nodes.merge_dataset import merge_dataset_node
from analyst.nodes.sup_planner import planner_node
from analyst.nodes.tool_executor import tool_executor_node
from analyst.nodes.visualization import visualization_node


def build_graph() -> StateGraph:
    """Construct the multi-agent analysis graph (uncompiled)."""

    workflow = StateGraph(GraphState)

    # ── Register Nodes ────────────────────────────────────────────────────
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("direct_answer", direct_answer_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("merge_dataset", merge_dataset_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("visualization", visualization_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("final_response", final_response_node)

    # ── Entry Point ───────────────────────────────────────────────────────
    workflow.add_edge(START, "intent_classifier")

    # ── Router: intent_classifier → direct_answer OR planner ──────────────
    workflow.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        ["direct_answer", "planner"],
    )

    # ── Simple path: direct_answer → END ──────────────────────────────────
    workflow.add_edge("direct_answer", END)

    # ── Complex path: planner → fan-out to parallel agents ────────────────
    workflow.add_conditional_edges(
        "planner",
        fan_out_to_tools,
        ["tool_executor", "merge_dataset"],
    )

    # ── All agents converge to merge_dataset ──────────────────────────────
    workflow.add_edge("tool_executor", "merge_dataset")

    # ── merge → analysis ──────────────────────────────────────────────────
    workflow.add_edge("merge_dataset", "analysis")

    # ── analysis → chart_check (conditional) ──────────────────────────────
    workflow.add_conditional_edges(
        "analysis",
        chart_check,
        ["visualization", "evaluator"],
    )

    # ── visualization → evaluator ─────────────────────────────────────────
    workflow.add_edge("visualization", "evaluator")

    # ── evaluator → final_response → END ──────────────────────────────────
    workflow.add_edge("evaluator", "final_response")
    workflow.add_edge("final_response", END)

    return workflow


def compile_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Build and compile the graph with an optional checkpointer.

    Args:
        checkpointer: An already-initialised checkpointer instance
                      (e.g. AsyncPostgresSaver created in the FastAPI lifespan).
                      If None the graph compiles without persistence.
    """
    workflow = build_graph()

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()

