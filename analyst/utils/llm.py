"""LLM singleton — configures the ChatOpenAI instance used across all nodes."""

from langchain_openai import ChatOpenAI

from analyst.config import OPENAI_API_KEY, OPENAI_MODEL


def get_llm(temperature: float = 0.0, model: str | None = None) -> ChatOpenAI:
    """Return a ChatOpenAI instance.

    Uses the project-level OPENAI_API_KEY and model defaults.
    Nodes that need different temperature/model can override.
    """
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=model or OPENAI_MODEL,
        temperature=temperature,
        streaming=True
    )
