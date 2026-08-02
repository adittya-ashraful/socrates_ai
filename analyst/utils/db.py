"""Database utilities — engine registries (async + sync) and schema introspection.

Async engines are for FastAPI endpoints (future).
Sync engines are for tools like ``exe_sql`` that use ``pd.read_sql()``.
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

load_dotenv()

# ── Async Engine Registry ────────────────────────────────────────────────
_async_engines: dict[str, AsyncEngine] = {}


def register_engine(name: str, url: str) -> AsyncEngine:
    engine = create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
    )
    _async_engines[name] = engine
    return engine


def get_async_engines() -> dict[str, AsyncEngine]:
    if not _async_engines:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        register_engine("default", database_url)
    return _async_engines


async def clear_engines() -> None:
    for engine in _async_engines.values():
        await engine.dispose()
    _async_engines.clear()


# ── Sync Engine Registry ─────────────────────────────────────────────────
_sync_engines: dict[str, Engine] = {}


def _async_url_to_sync(url: str) -> str:
    """Convert ``postgresql+asyncpg://`` to ``postgresql://``."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


def register_sync_engine(name: str, url: str) -> Engine:
    sync_url = _async_url_to_sync(url)
    engine = create_engine(
        sync_url,
        echo=False,
        pool_pre_ping=True,
    )
    _sync_engines[name] = engine
    return engine


def get_sql_engines() -> dict[str, Engine]:
    """Return sync engine registry — used by ``exe_sql`` and other tools."""
    if not _sync_engines:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        register_sync_engine("default", database_url)
    return _sync_engines


def clear_sync_engines() -> None:
    for engine in _sync_engines.values():
        engine.dispose()
    _sync_engines.clear()


# ── Schema Introspection ─────────────────────────────────────────────────

def get_db_schema(engine_name: str = "default") -> dict:
    """Auto-introspect database schema at startup.

    Returns a dict like::

        {
            "table_name": {
                "columns": [
                    {"name": "id", "type": "INTEGER", "nullable": False},
                    ...
                ],
                "primary_keys": ["id"]
            }
        }
    """
    engines = get_sql_engines()
    if engine_name not in engines:
        raise ValueError(f"Unknown engine: {engine_name}")

    engine = engines[engine_name]
    inspector = inspect(engine)
    schema: dict = {}

    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
            })

        pk = inspector.get_pk_constraint(table_name)
        schema[table_name] = {
            "columns": columns,
            "primary_keys": pk.get("constrained_columns", []) if pk else [],
        }

    return schema


# ── Session DataFrame Store ──────────────────────────────────────────────
_session_dataframes: dict[str, dict[str, pd.DataFrame]] = {}


def register_session_dataframe(
    session_id: str, name: str, df: pd.DataFrame
) -> None:
    """Store a DataFrame for the given session."""
    _session_dataframes.setdefault(session_id, {})[name] = df


def get_session_dataframes(session_id: str) -> dict[str, pd.DataFrame]:
    """Return all DataFrames stored for the session."""
    return _session_dataframes.get(session_id, {})


def clear_session_dataframes(session_id: str | None = None) -> None:
    """Clear DataFrames — for a specific session or all sessions."""
    if session_id:
        _session_dataframes.pop(session_id, None)
    else:
        _session_dataframes.clear()
