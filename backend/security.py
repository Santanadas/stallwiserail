import os
import re
import base64
import hashlib
import secrets
from typing import Optional
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

JWT_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    return os.environ.get("JWT_SECRET", "stallwise_default_super_secret_jwt_key_2026")


# ---------- Password hashing ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------- Input sanitization & safety ----------
def sanitize_text(val: Optional[str], max_len: int = 5000) -> str:
    """Strips dangerous control characters and null bytes from text."""
    if not val:
        return ""
    # Remove null bytes and dangerous control chars
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(val))
    return clean[:max_len].strip()


def is_safe_image_path(path: Optional[str]) -> bool:
    """Verifies that an image path is a safe relative file path or standard HTTPS URL."""
    if not path:
        return True
    p = path.strip()
    if p.startswith("/api/files/"):
        # Validate path format: marketo/uploads/...
        return bool(re.match(r"^/api/files/[a-zA-Z0-9_\-/\.]+$", p)) and ".." not in p
    if p.startswith("https://") or p.startswith("http://"):
        return not any(x in p.lower() for x in ("javascript:", "data:", "vbscript:", "<", ">"))
    return False


# ---------- In-Memory Sliding Window Rate Limiter ----------
_rate_limits: dict = {}


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """Sliding-window rate limiter. Returns True if allowed, False if exceeded."""
    now_ts = datetime.now(timezone.utc).timestamp()
    history = _rate_limits.setdefault(key, [])
    # Filter out entries older than window
    cutoff = now_ts - window_seconds
    _rate_limits[key] = [t for t in history if t > cutoff]
    if len(_rate_limits[key]) >= max_requests:
        return False
    _rate_limits[key].append(now_ts)
    return True


# ---------- JWT ----------
def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=180),
        "type": "access",
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=365),
        "type": "refresh",
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])


# ---------- AES-256-GCM secret encryption ----------
def _enc_key() -> bytes:
    key = os.environ.get("ENCRYPTION_KEY", "stallwise_default_aes_encryption_key_2026")
    return hashlib.sha256(key.encode("utf-8")).digest()


def encrypt_secret(plaintext: str) -> str:
    aes = AESGCM(_enc_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def decrypt_secret(token: str) -> str:
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    aes = AESGCM(_enc_key())
    return aes.decrypt(nonce, ct, None).decode("utf-8")


# ---------- OTP ----------
def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp: str) -> str:
    return hash_password(otp)


def verify_otp(otp: str, hashed: str) -> bool:
    return verify_password(otp, hashed)
