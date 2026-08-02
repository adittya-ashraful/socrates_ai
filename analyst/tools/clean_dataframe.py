import pandas as pd


def clean_dataframe(
    df: pd.DataFrame,
    required_cols: list[str] | None = None,
    dtypes: dict[str, str] | None = None,
    drop_duplicates: bool = True,
) -> pd.DataFrame:
    """Clean a DataFrame: drop nulls in required cols, dedup, cast types.

    Returns a new (cleaned) DataFrame.
    """
    df = df.copy()

    if required_cols:
        df = df.dropna(subset=required_cols)

    if drop_duplicates:
        df = df.drop_duplicates()

    if dtypes:
        for col, dtype in dtypes.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype)

    return df
