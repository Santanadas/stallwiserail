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
