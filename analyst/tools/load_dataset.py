import pandas as pd


def load_dataset(path: str) -> pd.DataFrame:
    """Load a CSV or Parquet file into a DataFrame.

    Raises ValueError for unsupported formats.
    """
    if path.endswith(".csv"):
        return pd.read_csv(path)
    elif path.endswith((".parquet", ".pq")):
        return pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file format: {path}")
