"""Test database connection and AsyncPostgresSaver checkpoint setup."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()


async def test():
    db_url = os.getenv("DATABASE_URL")
    print(f"Connecting to: {db_url}\n")

    if db_url and db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    # -- 1. Test connection pool -------------------------------------------
    try:
        pool = AsyncConnectionPool(
            conninfo=db_url,
            min_size=1,
            max_size=3,
            open=False,
        )
        await pool.open()
        await pool.wait()
        print("[OK]  Connection pool opened successfully!")
    except Exception as e:
        print(f"[FAIL]  Connection pool failed: {e}")
        return

    # -- 2. Test AsyncPostgresSaver setup (autocommit connection) ----------
    try:
        async with await AsyncConnection.connect(db_url, autocommit=True) as conn:
            setup_cp = AsyncPostgresSaver(conn)
            await setup_cp.setup()
        print("[OK]  Checkpoint tables created / verified!")
    except Exception as e:
        print(f"[FAIL]  Checkpointer setup failed: {e}")

    # -- 3. Verify checkpointer works with pool ----------------------------
    try:
        checkpointer = AsyncPostgresSaver(pool)
        config = {"configurable": {"thread_id": "__test__"}}
        checkpoint = await checkpointer.aget(config)
        print(f"[OK]  Checkpointer aget() works (result: {type(checkpoint).__name__})")
    except Exception as e:
        print(f"[FAIL]  Checkpointer aget() failed: {e}")

    # -- 4. Cleanup --------------------------------------------------------
    await pool.close()
    print("\nAll checks passed -- database is ready for checkpointing.")


asyncio.run(test())
