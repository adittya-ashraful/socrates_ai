"""Sanitize data structures for LangGraph checkpoint serialization.

LangGraph's checkpointer uses msgpack, which cannot serialize numpy types
(numpy.float64, numpy.int64, etc.). This module provides a recursive
converter that turns all numpy scalars and arrays into native Python types.
"""

import math
from typing import Any

import numpy as np


def sanitize_numpy(obj: Any) -> Any:
    """Recursively convert numpy types to Python-native equivalents.

    Handles: scalars, arrays, dicts, lists, tuples, and sets.
    NaN / Inf float values are converted to None to avoid downstream
    JSON / msgpack issues.
    """
    # ── numpy scalar types ────────────────────────────────────────────────
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return sanitize_numpy(obj.tolist())

    # ── Python float edge cases (NaN / Inf from pandas) ───────────────────
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # ── containers ────────────────────────────────────────────────────────
    if isinstance(obj, dict):
        return {sanitize_numpy(k): sanitize_numpy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_numpy(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(sanitize_numpy(item) for item in obj)
    if isinstance(obj, set):
        return {sanitize_numpy(item) for item in obj}

    return obj
