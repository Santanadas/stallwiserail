import os
import uuid
import logging

logger = logging.getLogger("marketo.storage")

# Local filesystem storage for development.
# Falls back to ./uploads relative to the backend directory.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))
APP_NAME = "marketo"

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp",
}


def init_storage(force: bool = False) -> str:
    """Ensure the local uploads directory exists."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def _resolve(path: str) -> str:
    """Resolve ``path`` to an absolute location that is guaranteed to sit inside
    UPLOAD_DIR. Raises ValueError on any traversal attempt."""
    base = os.path.realpath(UPLOAD_DIR)
    # Reject absolute paths and anything with a parent-dir segment outright.
    p = (path or "").lstrip("/\\")
    full = os.path.realpath(os.path.join(base, p))
    if full != base and not full.startswith(base + os.sep):
        raise ValueError("Path escapes storage root")
    return full


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Write file to local filesystem."""
    full_path = _resolve(path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(data)
    return {"path": path, "size": len(data)}


def get_object(path: str):
    """Read file from local filesystem."""
    full_path = _resolve(path)
    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File not found: {path}")
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    content_type = MIME_TYPES.get(ext, "application/octet-stream")
    with open(full_path, "rb") as f:
        return f.read(), content_type


def build_path(user_id: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{APP_NAME}/uploads/{user_id}/{uuid.uuid4().hex}.{ext}"


# ---------------------------------------------------------------------------
# Durable storage.
#
# put_object/get_object above write to the container filesystem, which Railway
# rebuilds on every deploy — and `uploads` is in .dockerignore, so the files are
# not even in the image. Product photos uploaded on Monday were gone on Tuesday,
# leaving sellers with a shop full of broken images and no idea why.
#
# The bytes now go in the database, which is the only durable store the app has
# without asking the seller to configure object storage first. Reads still check
# the filesystem afterwards, so anything already written there keeps working.
# ---------------------------------------------------------------------------
MAX_OBJECT_BYTES = 5 * 1024 * 1024


async def put(path: str, data: bytes, content_type: str, owner_id: str = "") -> dict:
    """Store an object durably. Falls back to disk if the database refuses."""
    import db  # local: db does not import storage, and this keeps it that way

    if len(data) > MAX_OBJECT_BYTES:
        raise ValueError("Object too large")
    from datetime import datetime, timezone
    created = datetime.now(timezone.utc).isoformat()
    try:
        await db.execute(
            """
            INSERT INTO media (path, owner_id, content_type, bytes, size, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (path) DO UPDATE
            SET bytes = EXCLUDED.bytes, content_type = EXCLUDED.content_type,
                size = EXCLUDED.size
            """,
            path, owner_id, content_type, data, len(data), created)
        return {"path": path, "size": len(data), "durable": True}
    except Exception as exc:
        # Better a photo that survives until the next restart than an upload
        # the seller cannot complete at all.
        logger.error("media: database write failed for %s (%s) — falling back to disk",
                     path, exc)
        result = put_object(path, data, content_type)
        result["durable"] = False
        return result


async def get(path: str):
    """Read an object: database first, then any file left on disk."""
    import db

    try:
        row = await db.fetch_one(
            "SELECT content_type, bytes FROM media WHERE path = $1", path)
    except Exception as exc:
        logger.error("media: database read failed for %s (%s)", path, exc)
        row = None
    if row:
        raw = row["bytes"]
        return (bytes(raw) if not isinstance(raw, bytes) else raw), row["content_type"]
    # Uploaded before the move, or written by the disk fallback above.
    return get_object(path)


async def delete(path: str) -> None:
    import db

    try:
        await db.execute("DELETE FROM media WHERE path = $1", path)
    except Exception as exc:
        logger.error("media: database delete failed for %s (%s)", path, exc)
