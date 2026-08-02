import json

from analyst.utils.helpers import extract_json
from analyst.utils.llm import get_llm

GENERATE_SQL_PROMPT = """\
Generate a SQL query based on the following:
Intent: {intent}
Available schema: {schema}
Filters: {filters}

Rules:
- Use only columns that exist in the schema
- Be precise and minimal
- Return ONLY the raw SQL query, no markdown or explanation
"""


def generate_sql(
    intent: str,
    schema: dict,
    filters: dict | None = None,
) -> str:
    """Generate a SQL query from natural language intent and schema.

    Returns the raw SQL string.
    """
    llm = get_llm(temperature=0.0)
    response = llm.invoke(
        GENERATE_SQL_PROMPT.format(
            intent=intent,
            schema=json.dumps(schema, indent=2),
            filters=json.dumps(filters or {}),
        )
    )
    # Strip any markdown fencing
    sql = response.content.strip()
    if sql.startswith("```"):
        sql = extract_json(sql)  # Reuse fence-stripping logic
    return sql
