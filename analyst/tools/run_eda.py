import pandas as pd

from analyst.utils.sanitize import sanitize_numpy


def run_eda(df: pd.DataFrame, ops: list[str]) -> dict:
    """Run exploratory data analysis operations on a DataFrame.

    Supported ops: summary, correlations, nulls, outliers.
    Returns a dict keyed by operation name.
    """
    results: dict = {}

    for op in ops:
        if op == "summary":
            results["summary"] = df.describe(include="all").to_dict()
        elif op == "correlations":
            numeric = df.select_dtypes("number")
            if not numeric.empty:
                results["correlations"] = numeric.corr().to_dict()
            else:
                results["correlations"] = {}
        elif op == "nulls":
            results["nulls"] = df.isnull().sum().to_dict()
        elif op == "outliers":
            numeric = df.select_dtypes("number")
            if not numeric.empty:
                z = ((numeric - numeric.mean()) / numeric.std()).abs()
                results["outliers"] = (z > 3).sum().to_dict()
            else:
                results["outliers"] = {}

    return sanitize_numpy(results)
