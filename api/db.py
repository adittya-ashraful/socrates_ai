"""Database table management for Socrates AI application tables.

Creates and manages the `threads` and `file_metadata` tables in PostgreSQL.
These are application-level tables, separate from LangGraph checkpoint tables.
"""

from __future__ import annotations

# ── SQL Statements ────────────────────────────────────────────────────────

CREATE_THREADS_TABLE = """\
CREATE TABLE IF NOT EXISTS threads (
    thread_id   TEXT PRIMARY KEY,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message TEXT
);
"""

CREATE_FILE_METADATA_TABLE = """\
CREATE TABLE IF NOT EXISTS file_metadata (
    file_id      TEXT PRIMARY KEY,
    thread_id    TEXT,
    filename     TEXT NOT NULL,
    file_path    TEXT NOT NULL,
    size_bytes   BIGINT NOT NULL DEFAULT 0,
    content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_thread FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE SET NULL
);
"""

CREATE_INDEXES = """\
CREATE INDEX IF NOT EXISTS idx_file_metadata_thread ON file_metadata(thread_id);
CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at DESC);
"""


async def setup_app_tables(pool) -> None:
    """Create application tables if they don't exist.

    Args:
        pool: An ``AsyncConnectionPool`` (psycopg) from the app lifespan.
    """
    async with pool.connection() as conn:
        await conn.execute(CREATE_THREADS_TABLE)
        await conn.execute(CREATE_FILE_METADATA_TABLE)
        await conn.execute(CREATE_INDEXES)
        await conn.commit()


# ── Thread CRUD ───────────────────────────────────────────────────────────

async def create_thread(pool, thread_id: str, title: str | None = None) -> dict:
    """Insert a new thread row and return it as a dict."""
    async with pool.connection() as conn:
        row = await conn.execute(
            """\
            INSERT INTO threads (thread_id, title)
            VALUES (%s, %s)
            ON CONFLICT (thread_id) DO NOTHING
            RETURNING thread_id, title, created_at, updated_at, last_message
            """,
            (thread_id, title),
        )
        result = await row.fetchone()
        await conn.commit()

    if result is None:
        # Already existed — fetch it
        return await get_thread(pool, thread_id)

    return _thread_row_to_dict(result)


async def get_thread(pool, thread_id: str) -> dict | None:
    """Fetch a single thread by ID."""
    async with pool.connection() as conn:
        row = await conn.execute(
            "SELECT thread_id, title, created_at, updated_at, last_message FROM threads WHERE thread_id = %s",
            (thread_id,),
        )
        result = await row.fetchone()

    if result is None:
        return None
    return _thread_row_to_dict(result)


async def list_threads(pool, limit: int = 50, offset: int = 0) -> list[dict]:
    """List threads ordered by most recently updated."""
    async with pool.connection() as conn:
        rows = await conn.execute(
            """\
            SELECT thread_id, title, created_at, updated_at, last_message
            FROM threads
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        results = await rows.fetchall()

    return [_thread_row_to_dict(r) for r in results]


async def update_thread(pool, thread_id: str, last_message: str | None = None, title: str | None = None) -> None:
    """Update thread metadata (last_message, title, updated_at)."""
    parts = ["updated_at = NOW()"]
    params: list = []

    if last_message is not None:
        parts.append("last_message = %s")
        params.append(last_message[:500])  # truncate for storage
    if title is not None:
        parts.append("title = %s")
        params.append(title[:200])

    params.append(thread_id)

    async with pool.connection() as conn:
        await conn.execute(
            f"UPDATE threads SET {', '.join(parts)} WHERE thread_id = %s",
            tuple(params),
        )
        await conn.commit()


async def delete_thread(pool, thread_id: str) -> bool:
    """Delete a thread and its associated file metadata. Returns True if deleted."""
    async with pool.connection() as conn:
        # file_metadata FK has ON DELETE SET NULL, but let's clean up explicitly
        await conn.execute("DELETE FROM file_metadata WHERE thread_id = %s", (thread_id,))
        result = await conn.execute("DELETE FROM threads WHERE thread_id = %s", (thread_id,))
        await conn.commit()
        return result.rowcount > 0


# ── File Metadata CRUD ───────────────────────────────────────────────────

async def insert_file_metadata(
    pool,
    file_id: str,
    filename: str,
    file_path: str,
    size_bytes: int,
    content_type: str,
    thread_id: str | None = None,
) -> dict:
    """Insert file metadata and return it."""
    async with pool.connection() as conn:
        row = await conn.execute(
            """\
            INSERT INTO file_metadata (file_id, thread_id, filename, file_path, size_bytes, content_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING file_id, thread_id, filename, file_path, size_bytes, content_type, created_at
            """,
            (file_id, thread_id, filename, file_path, size_bytes, content_type),
        )
        result = await row.fetchone()
        await conn.commit()

    return _file_row_to_dict(result)


async def get_file_metadata(pool, file_id: str) -> dict | None:
    """Fetch a single file's metadata."""
    async with pool.connection() as conn:
        row = await conn.execute(
            "SELECT file_id, thread_id, filename, file_path, size_bytes, content_type, created_at FROM file_metadata WHERE file_id = %s",
            (file_id,),
        )
        result = await row.fetchone()

    if result is None:
        return None
    return _file_row_to_dict(result)


async def get_files_by_ids(pool, file_ids: list[str]) -> list[dict]:
    """Fetch metadata for multiple files by their IDs."""
    if not file_ids:
        return []

    placeholders = ", ".join(["%s"] * len(file_ids))
    async with pool.connection() as conn:
        rows = await conn.execute(
            f"SELECT file_id, thread_id, filename, file_path, size_bytes, content_type, created_at FROM file_metadata WHERE file_id IN ({placeholders})",
            tuple(file_ids),
        )
        results = await rows.fetchall()

    return [_file_row_to_dict(r) for r in results]


async def list_files_for_thread(pool, thread_id: str) -> list[dict]:
    """List all files associated with a thread."""
    async with pool.connection() as conn:
        rows = await conn.execute(
            "SELECT file_id, thread_id, filename, file_path, size_bytes, content_type, created_at FROM file_metadata WHERE thread_id = %s ORDER BY created_at",
            (thread_id,),
        )
        results = await rows.fetchall()

    return [_file_row_to_dict(r) for r in results]


async def link_file_to_thread(pool, file_id: str, thread_id: str) -> None:
    """Associate an uploaded file with a thread."""
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE file_metadata SET thread_id = %s WHERE file_id = %s",
            (thread_id, file_id),
        )
        await conn.commit()


async def delete_file_metadata(pool, file_id: str) -> bool:
    """Delete a file's metadata row. Returns True if deleted."""
    async with pool.connection() as conn:
        result = await conn.execute("DELETE FROM file_metadata WHERE file_id = %s", (file_id,))
        await conn.commit()
        return result.rowcount > 0


# ── Helpers ───────────────────────────────────────────────────────────────

def _thread_row_to_dict(row) -> dict:
    """Convert a psycopg row tuple to a thread dict."""
    return {
        "thread_id": row[0],
        "title": row[1],
        "created_at": row[2].isoformat() if row[2] else None,
        "updated_at": row[3].isoformat() if row[3] else None,
        "last_message": row[4],
    }


def _file_row_to_dict(row) -> dict:
    """Convert a psycopg row tuple to a file metadata dict."""
    return {
        "file_id": row[0],
        "thread_id": row[1],
        "filename": row[2],
        "file_path": row[3],
        "size_bytes": row[4],
        "content_type": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
    }
