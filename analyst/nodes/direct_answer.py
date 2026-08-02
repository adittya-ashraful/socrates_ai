from analyst.utils.llm import get_llm

DIRECT_ANSWER_PROMPT = """
You are Socrates AI, an advanced AI Data Analyst.

Answer the user's question directly.
When asked about your capabilities, explain that you can:
- Query SQL databases
- Write and execute Python code for data analysis
- Process and analyze uploaded datasets (CSV, Excel, etc.)
- Create data visualizations and charts
- Perform web searches to enrich data analysis

Rules:
- Do not use or assume access to external tools for simple chat.
- Do not invent facts from databases or files.
- If answering requires a dataset, uploaded file, search, SQL, or Python,
  state that analysis tools are required instead of guessing.
- Keep the answer clear and concise.

User:
{message}

Conversation History:
{history}
"""
from analyst.schemas.state import GraphState
from langchain_core.messages import AIMessage


def direct_answer_node(state: GraphState) -> dict:
    """Answer simple chat requests without using any tools."""

    llm = get_llm(temperature=0.2)

    # Format the history
    history_str = ""
    for msg in state.get("messages", []):
        role = "User" if msg.type == "human" else "AI"
        history_str += f"{role}: {msg.content}\n"
        
    prompt = DIRECT_ANSWER_PROMPT.format(
        message=state["user_query"],
        history=history_str.strip() or "No previous history."
    )

    response = llm.invoke(prompt)

    return {
        "final_answer": response.content,
        "messages": [AIMessage(content=response.content)]
    }