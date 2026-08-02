"""FileManager — handles file uploads with persistent metadata in PostgreSQL.

Files are stored on disk under ``uploads/`` (project-relative).
Metadata (file_id, filename, path, size, content_type) is persisted in
the ``file_metadata`` PostgreSQL table via the ``api.db`` module.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import UploadFile

from api.db import (
    delete_file_metadata,
    get_file_metadata,
    get_files_by_ids,
    insert_file_metadata,
    link_file_to_thread,
    list_files_for_thread,
)

if TYPE_CHECKING:
    from psycopg_pool import AsyncConnectionPool


# Default upload directory (project-relative)
_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


class FileManager:
    """Manages file uploads: saves to disk and persists metadata to PostgreSQL."""

    def __init__(self, pool: AsyncConnectionPool, upload_dir: Path | None = None):
        self._pool = pool
        self._upload_dir = upload_dir or _UPLOAD_DIR
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile, thread_id: str | None = None) -> dict:
        """Save an uploaded file to disk and record metadata in PostgreSQL.

        Args:
            file: FastAPI UploadFile from the request.
            thread_id: Optional thread to associate the file with.

        Returns:
            File metadata dict with file_id, filename, path, size, content_type.
        """
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        dest_path = self._upload_dir / safe_filename

        # Stream file to disk
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        size_bytes = dest_path.stat().st_size
        content_type = file.content_type or "application/octet-stream"

        # Persist metadata to PostgreSQL
        metadata = await insert_file_metadata(
            pool=self._pool,
            file_id=file_id,
            filename=file.filename,
            file_path=str(dest_path),
            size_bytes=size_bytes,
            content_type=content_type,
            thread_id=thread_id,
        )

        return metadata

    async def get(self, file_id: str) -> dict | None:
        """Retrieve file metadata by ID."""
        return await get_file_metadata(self._pool, file_id)

    async def get_many(self, file_ids: list[str]) -> list[dict]:
        """Retrieve metadata for multiple files."""
        return await get_files_by_ids(self._pool, file_ids)

    async def list_for_thread(self, thread_id: str) -> list[dict]:
        """List all files linked to a conversation thread."""
        return await list_files_for_thread(self._pool, thread_id)

    async def link_to_thread(self, file_id: str, thread_id: str) -> None:
        """Associate an existing file with a thread."""
        await link_file_to_thread(self._pool, file_id, thread_id)

    async def delete(self, file_id: str) -> bool:
        """Delete a file from disk and remove its metadata.

        Returns True if the file was found and deleted.
        """
        meta = await get_file_metadata(self._pool, file_id)
        if meta is None:
            return False

        # Remove from disk
        disk_path = Path(meta["file_path"])
        if disk_path.exists():
            disk_path.unlink()

        # Remove metadata from DB
        return await delete_file_metadata(self._pool, file_id)
