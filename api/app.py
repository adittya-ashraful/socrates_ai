"""FastAPI application factory for Socrates AI.

Creates the app with:
- Lifespan handler that sets up AsyncConnectionPool + AsyncPostgresSaver
  and compiles the LangGraph on startup
- Application tables (threads, file_metadata) created on startup
- FileManager for persistent file uploads
- CORS middleware (all origins allowed for local dev)
- Router mounted at /api
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from analyst.graph.builder import compile_graph
from api.db import setup_app_tables
from api.files import FileManager
from api.routes import router

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: open connection pool -> create checkpointer -> compile graph.
    Shutdown: close pool cleanly.
    """
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )
    # Supabase URLs sometimes come with the asyncpg scheme -- normalise
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    # 1. Connection pool
    # prepare_threshold=None disables prepared statements — required for
    # Supabase / PgBouncer which runs in transaction pooling mode.
    # NOTE: 0 means "prepare immediately", None means "never prepare".
    pool = AsyncConnectionPool(
        conninfo=db_url,
        min_size=2,
        max_size=10,
        open=False,
        kwargs={"prepare_threshold": None},
    )
    await pool.open()
    await pool.wait()          # block until min_size connections are ready
    print("[OK]  Database connection pool opened.")

    # 2. Async checkpointer 
    checkpointer = AsyncPostgresSaver(pool)

    # setup() runs CREATE INDEX CONCURRENTLY which needs autocommit.
    # Use a one-off direct connection for this, then close it.
    try:
        async with await AsyncConnection.connect(db_url, autocommit=True) as conn:
            setup_cp = AsyncPostgresSaver(conn)
            await setup_cp.setup()
        print("[OK]  Checkpoint tables ready.")
    except Exception as e:
        print(f"[WARN]  Checkpoint table setup skipped: {e}")
        print("        Tables may already exist -- continuing.")

    # 3. Application tables (threads, file_metadata)
    try:
        await setup_app_tables(pool)
        print("[OK]  Application tables ready (threads, file_metadata).")
    except Exception as e:
        print(f"[WARN]  Application table setup issue: {e}")
        print("        Tables may already exist -- continuing.")

    # 4. FileManager 
    file_manager = FileManager(pool)
    app.state.file_manager = file_manager
    print("[OK]  FileManager initialised.")

    # 5. Compile graph with the checkpointer
    app.state.graph = compile_graph(checkpointer=checkpointer)
    app.state.pool = pool
    app.state.checkpointer = checkpointer
    print("[OK]  LangGraph compiled with AsyncPostgresSaver.")

    yield

    # Shutdown
    await pool.close()
    print("[OK]  Database connection pool closed.")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""

    app = FastAPI(
        title="Socrates AI",
        description="Multi-Agent Data Analysis API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins for local development 
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    #  Routes 
    app.include_router(router)

    return app
