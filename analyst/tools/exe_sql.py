"""Pure SQL execution function.

Features: result caching with TTL, retry on OperationalError.
"""

import hashlib
import time

import pandas as pd
from sqlalchemy.exc import OperationalError

from analyst.config import SQL_CACHE_TTL
from analyst.utils.db import get_sql_engines
from analyst.utils.sanitize import sanitize_numpy

SQL_CACHE: dict ={}

def execute_sql(query: str, engine_name: str = "default") -> dict:
    """Execute a SQL query and return records, columns, and row count.

    Caches results by query hash for SQL_CACHE_TTL seconds.
    Retries up to 3 times on OperationalError.
    """
    engines = get_sql_engines()
    if engine_name not in engines:
        raise ValueError(f"Unknown engine: {engine_name}")
    engine = engines[engine_name]
    cache_key = hashlib.sha256(query.encode()).hexdigest()

    # Cache hit
    if cache_key in SQL_CACHE:
        entry = SQL_CACHE[cache_key]
        if time.time() - entry["ts"] < SQL_CACHE_TTL:
            return entry["data"]

    # Execute with retries
    for attempt in range(3):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(query, conn)
            result = sanitize_numpy({
                "records": df.to_dict(orient="records"),
                "columns": list(df.columns),
                "row_count": len(df),
            })
            SQL_CACHE[cache_key] = {"data": result, "ts": time.time()}
            return result
        except OperationalError:
            if attempt == 2:
                raise
            time.sleep(0.1 * (2 ** attempt))

    # Unreachable, but satisfies type checker
    raise RuntimeError("SQL execution failed after retries")
