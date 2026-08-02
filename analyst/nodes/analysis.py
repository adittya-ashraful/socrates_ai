"""Python Analysis Subgraph node — Clean → Transform → Analyze → Insights.

Implements the full analysis pipeline from the architecture:
1. Clean the merged dataset
2. Transform (type casting, feature engineering)
3. Analyze (EDA: summary stats, correlations, nulls, outliers)
4. Insights (LLM-generated narrative from analysis results)
"""

import json

import pandas as pd

from analyst.schemas.state import GraphState
from analyst.tools.clean_dataframe import clean_dataframe
from analyst.tools.run_eda import run_eda
from analyst.utils.llm import get_llm
from analyst.utils.sanitize import sanitize_numpy

INSIGHTS_PROMPT = """\
You are a senior data analyst. Based on the analysis results below,
generate clear, actionable insights.

User's original question:
{query}

Dataset shape: {row_count} rows × {col_count} columns
Columns: {columns}

Analysis results:
{analysis}

Search context (if any):
{search_context}

Rules:
- Focus on answering the user's question directly
- Highlight key findings, trends, and anomalies
- Use specific numbers from the data
- Be concise but thorough
- If the data doesn't fully answer the question, say so
"""


def analysis_node(state: GraphState) -> dict:
    """Run the full analysis pipeline: Clean → Transform → Analyze → Insights."""
    merged_data = state.get("merged_data", {})
    records = merged_data.get("records", [])
    search_context = merged_data.get("search_context", [])
    errors = []

    # If no tabular data, generate insights from search context alone
    if not records:
        if search_context:
            llm = get_llm(temperature=0.2)
            prompt = INSIGHTS_PROMPT.format(
                query=state.get("user_query", ""),
                row_count=0,
                col_count=0,
                columns="N/A",
                analysis="No tabular data available",
                search_context=json.dumps(search_context, indent=2)[:3000],
            )
            response = llm.invoke(prompt)
            return {
                "analysis_results": {"source": "search_only"},
                "insights": response.content,
                "execution_errors": [],
            }
        return {
            "analysis_results": None,
            "insights": "No data available to analyze.",
            "execution_errors": ["No data in merged_data"],
        }

    try:
        # 1. Clean
        df = pd.DataFrame(records)
        df = clean_dataframe(df, drop_duplicates=True)

        # 2. Transform — robust type inference
        for col in df.columns:
            if df[col].dtype == "object":
                # Remove common formatting that prevents numeric parsing
                cleaned = df[col].astype(str).str.replace(r'[$,%]', '', regex=True)
                # Replace common string nulls with actual NaNs
                cleaned = cleaned.replace(['', 'N/A', 'NA', 'null', 'None', 'nan', 'NaN'], pd.NA)
            else:
                cleaned = df[col]

            converted = pd.to_numeric(cleaned, errors="coerce")
            
            # If we successfully parsed more than 50% of the non-null values as numbers,
            # consider the column numeric and keep the converted values
            original_non_nulls = df[col].notna().sum()
            if original_non_nulls > 0 and (converted.notna().sum() / original_non_nulls) > 0.5:
                df[col] = converted

        # 3. Analyze — run EDA operations
        eda_results = run_eda(df, ops=["summary", "correlations", "nulls", "outliers"])

        analysis_results = sanitize_numpy({
            "eda": eda_results,
            "shape": {"rows": len(df), "columns": list(df.columns)},
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample": sanitize_numpy(df.head(5).to_dict(orient="records")),
        })

        # 4. Insights — LLM-generated narrative
        llm = get_llm(temperature=0.2)
        prompt = INSIGHTS_PROMPT.format(
            query=state.get("user_query", ""),
            row_count=len(df),
            col_count=len(df.columns),
            columns=", ".join(df.columns.tolist()),
            analysis=json.dumps(eda_results, indent=2, default=str)[:4000],
            search_context=(
                json.dumps(search_context, indent=2)[:2000]
                if search_context else "None"
            ),
        )
        response = llm.invoke(prompt)

        return {
            "analysis_results": analysis_results,
            "insights": response.content,
            "execution_errors": [],
        }

    except Exception as e:
        errors.append(f"Analysis pipeline error: {e}")
        return {
            "analysis_results": None,
            "insights": f"Analysis failed: {e}",
            "execution_errors": errors,
        }
