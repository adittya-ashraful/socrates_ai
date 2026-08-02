"""Shared helper functions for node implementations."""

import re
from copy import deepcopy


def extract_json(text: str) -> str:
    """Extract a JSON object or array from LLM output.

    Handles markdown code fences, leading/trailing text, etc.
    Returns the raw JSON string for json.loads().
    """
    # Try to find ```json ... ``` blocks first
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # Try to find raw JSON object or array
    for pattern in [r"(\[.*\])", r"(\{.*\})"]:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            return m.group(1).strip()

    return text.strip()


def mark_step(plan: list[dict], index: int, status: str) -> list[dict]:
    """Return a copy of the plan with the step at *index* marked with *status*."""
    plan = deepcopy(plan)
    if 0 <= index < len(plan):
        plan[index]["status"] = status
    return plan


def format_history(history: list[dict], n: int | None = None) -> str:
    """Format chat_history entries into a readable string for prompts."""
    entries = history[-n:] if n else history
    lines = []
    for entry in entries:
        role = entry.get("role", "unknown").capitalize()
        content = entry.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
