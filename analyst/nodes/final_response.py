"""Final Response node — assembles the user-facing answer.

Combines insights, chart info, and evaluator feedback into
a polished final response for the user.
"""

from analyst.schemas.state import GraphState
from analyst.utils.llm import get_llm
from langchain_core.messages import AIMessage

FINAL_RESPONSE_PROMPT = """\
You are a senior data analyst presenting findings to the user.

Compose a clear, complete response based on:

User's question:
{query}

Analysis insights:
{insights}

Chart: {chart_info}

Quality evaluation:
- Score: {eval_score}
- Feedback: {eval_feedback}
- Suggestions: {eval_suggestions}

Rules:
- Lead with the direct answer to the user's question
- Include key data points and findings
- If a chart was generated, mention it and describe what it shows
- If the evaluator found issues, address them honestly
- Be professional but approachable
- Use markdown formatting for readability
"""


def final_response_node(state: GraphState) -> dict:
    """Assemble the final response from all pipeline outputs."""
    evaluation = state.get("evaluation", {})
    chart_result = state.get("chart_result")

    # Prepare chart info
    if chart_result:
        chart_info = (
            f"A {chart_result.get('type', 'chart')} chart titled "
            f"'{chart_result.get('title', 'Chart')}' was generated."
        )
    else:
        chart_info = "No chart was generated."

    llm = get_llm(temperature=0.3)
    prompt = FINAL_RESPONSE_PROMPT.format(
        query=state.get("user_query", ""),
        insights=state.get("insights", "No insights available")[:4000],
        chart_info=chart_info,
        eval_score=evaluation.get("score", "N/A"),
        eval_feedback=evaluation.get("feedback", "N/A"),
        eval_suggestions=evaluation.get("suggestions", "none"),
    )

    response = llm.invoke(prompt)

    # Append chart path if available
    final_text = response.content
    if chart_result and chart_result.get("chart_path"):
        final_text += f"\n\n📊 Chart saved: `{chart_result['chart_path']}`"

    return {
        "final_answer": final_text,
        "messages": [AIMessage(content=final_text)],
    }
