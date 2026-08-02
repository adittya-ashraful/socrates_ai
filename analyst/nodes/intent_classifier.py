import json

from analyst.schemas.state import GraphState
from analyst.utils.helpers import extract_json
from analyst.utils.llm import get_llm

INTENT_PROMPT = """
You are the routing classifier for an AI analytics assistant.

Classify the user's message into exactly one intent.

Intent:

- chat
    Casual conversation, explanation, coding help, brainstorming, greetings.
    No external tools required.

- task
    Requires one or more tools such as SQL, Python, Search, File retrieval,
    statistics, plotting, reporting, visualization, or data analysis.
    IMPORTANT: If the user has attached files, this is almost certainly a "task".

- followup
    Depends on previous analytical context or previous tool results.

Priority:

followup > task > chat

Use followup ONLY when understanding the request requires previous analysis.
If files are attached, default to "task" unless the message is clearly unrelated to the files.

Conversation

Message:
{message}

Current topic:
{topic}

Turn state:
{turn_state}

Previous intent:
{prior_intent}

Attached files:
{attached_files}

Respond ONLY with valid JSON, no markdown:
{{"intent": "<intent>", "confidence": <0.0–1.0>, "reason": "<one sentence>"}}
"""

def intent_classifier_node(state: GraphState) -> dict:
    """Classify user intent using the LLM.

    Returns partial state with intent and intent_confidence.
    """
    llm = get_llm(temperature=0.0)

    # Build file info string for the prompt
    uploaded_files = state.get("uploaded_files", [])
    if uploaded_files:
        file_lines = [
            f"- {f.get('filename', 'unknown')} ({f.get('content_type', 'unknown')})"
            for f in uploaded_files
        ]
        attached_files_str = "\n".join(file_lines)
    else:
        attached_files_str = "None"

    prompt = INTENT_PROMPT.format(
        message=state.get("sanitized_message", state.get("user_query", "")),
        topic=state.get("topic", "none"),
        turn_state=state.get("turn_state", "new"),
        prior_intent=state.get("intent", "none"),
        attached_files=attached_files_str,
    )

    response = llm.invoke(prompt)
    parsed = json.loads(extract_json(response.content))

    return {
        "intent": parsed["intent"],
        "intent_confidence": parsed["confidence"],
        "intent_reason": parsed["reason"]
    }