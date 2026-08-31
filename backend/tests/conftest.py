"""Test harness.

Runs the real FastAPI app in-process against the SQLite engine, with a fresh
database per test. External services (Razorpay, Brevo) are never called: the
Razorpay client is faked, and email is a no-op because no BREVO_API_KEY is set.
"""
import hashlib
import hmac
import importlib
import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# --- Environment must be set before server.py / security.py import ---------
os.environ.update(
    {
        "JWT_SECRET": "test-jwt-secret-value-at-least-32-bytes-long",
        "ENCRYPTION_KEY": "test-encryption-key-32chars-minimum!",
        "FRONTEND_URL": "http://localhost:3000",
        "DEV_OTP_ECHO": "true",
        "RAZORPAY_KEY_ID": "rzp_test_fake",
        "RAZORPAY_KEY_SECRET": "rzp_test_secret",
    }
)
for leak in ("DATABASE_URL", "POSTGRES_URL", "SUPABASE_DB_URL", "BREVO_API_KEY",
             "SENDINBLUE_API_KEY", "RAZORPAY_WEBHOOK_SECRET", "ANTHROPIC_API_KEY"):
    os.environ.pop(leak, None)

PLATFORM_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

# Passwords and OTPs are bcrypt-hashed. Production cost (12 rounds) makes the
# suite take minutes, so drop it to the minimum for tests only — the code path
# under test is identical, just cheaper.
import bcrypt as _bcrypt  # noqa: E402

_real_gensalt = _bcrypt.gensalt
_bcrypt.gensalt = lambda rounds=4, prefix=b"2b": _real_gensalt(4, prefix)


# --- A Razorpay stand-in --------------------------------------------------
class _FakeOrders:
    created = []

    def create(self, payload):
        oid = f"order_{uuid.uuid4().hex[:14]}"
        rec = {"id": oid, **payload}
        self.created.append(rec)
        return rec

    def fetch(self, order_id):
        for rec in self.created:
            if rec["id"] == order_id:
                return rec
        return {"id": order_id, "notes": {"interval": "monthly"}}


class FakeRazorpay:
    def __init__(self, *a, **k):
        self.order = _FakeOrders()


def razorpay_signature(*parts: str, secret: str = PLATFORM_SECRET) -> str:
    msg = "|".join(parts).encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def webhook_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# Set STALLWISE_TEST_PG to a PostgreSQL URL to run the whole suite against
# Postgres instead of SQLite. The production incident where published products
# vanished was a Postgres-only bug (lists bound to TEXT columns) that every
# SQLite-only test passed straight through — so this needs to be exercisable.
#
#   podman run -d --rm -e POSTGRES_PASSWORD=test -e POSTGRES_DB=stallwise \
#       -p 55432:5432 postgres:16-alpine
#   STALLWISE_TEST_PG=postgresql://postgres:test@127.0.0.1:55432/stallwise pytest
TEST_PG_URL = (os.environ.get("STALLWISE_TEST_PG") or "").strip()

_PG_TABLES = ("users", "pending_otps", "login_attempts", "password_reset_tokens",
              "user_sessions", "stores", "products", "orders", "seller_routes",
              "seller_gateways", "platform_plans")


def _reset_pg_schema():
    """Create the schema if absent, then empty every table."""
    import asyncio

    import asyncpg as _asyncpg

    import db as _db

    async def _run():
        conn = await _asyncpg.connect(TEST_PG_URL)
        try:
            await conn.execute(_db._PG_SCHEMA)
            await conn.execute(
                "TRUNCATE " + ", ".join(_PG_TABLES) + " RESTART IDENTITY CASCADE")
        finally:
            await conn.close()

    asyncio.run(_run())


def raw_execute(query: str, *args):
    """Run a statement against whichever engine the suite is using.

    Tests that need to reach past the API — rewinding a timestamp, inspecting
    ciphertext at rest — must not hardcode `db._get_sqlite_conn()`, or they
    silently write to a database the app isn't reading. Write the query in
    Postgres dialect ($1, $2), same rule as the application code.
    """
    import db as _db

    if TEST_PG_URL:
        import asyncio

        import asyncpg as _asyncpg

        async def _run():
            conn = await _asyncpg.connect(TEST_PG_URL)
            try:
                await conn.execute(query, *_db.encode_args(args))
            finally:
                await conn.close()

        return asyncio.run(_run())

    conn = _db._get_sqlite_conn()
    q, a = _db._pg_to_sqlite(query, args)
    with conn:
        conn.execute(q, a)


def raw_fetch_one(query: str, *args):
    """Read a row straight from the active engine. Returns a dict or None."""
    import db as _db

    if TEST_PG_URL:
        import asyncio

        import asyncpg as _asyncpg

        async def _run():
            conn = await _asyncpg.connect(TEST_PG_URL)
            try:
                row = await conn.fetchrow(query, *_db.encode_args(args))
                return dict(row) if row else None
            finally:
                await conn.close()

        return asyncio.run(_run())

    conn = _db._get_sqlite_conn()
    q, a = _db._pg_to_sqlite(query, args)
    cur = conn.cursor()
    cur.execute(q, a)
    return _db._row_to_dict(cur.fetchone())


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """A TestClient bound to a fresh database (SQLite by default)."""
    import db
    import route_service
    import security
    import server

    # The sliding-window rate limiter is process-global in-memory state, so it
    # leaks between tests and eventually 429s the whole suite. Reset it.
    security._rate_limits.clear()

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    if TEST_PG_URL:
        monkeypatch.setenv("DATABASE_URL", TEST_PG_URL)
        monkeypatch.setattr(db, "_pool", None, raising=False)
        monkeypatch.setattr(db, "_ENGINE", "sqlite", raising=False)
    else:
        # Fresh, isolated SQLite file for this test.
        monkeypatch.setattr(db, "DB_FILE", tmp_path / "test.db", raising=False)
        monkeypatch.setattr(db, "_sqlite_conn", None, raising=False)
        monkeypatch.setattr(db, "_pool", None, raising=False)
        monkeypatch.setattr(db, "_ENGINE", "sqlite", raising=False)

    # Never touch the real Razorpay API.
    _fake = FakeRazorpay()
    monkeypatch.setattr(route_service, "platform_client",
                        lambda: (_fake, "rzp_test_fake", PLATFORM_SECRET))
    monkeypatch.setattr("razorpay.Client", FakeRazorpay)

    from fastapi.testclient import TestClient

    if TEST_PG_URL:
        # Isolate this test. Done on a standalone connection before the app
        # starts: the app's pool is bound to the TestClient's event loop and
        # cannot be driven from another one.
        _reset_pg_schema()

    with TestClient(server.app) as client:
        if TEST_PG_URL:
            assert db._ENGINE == "postgres", (
                f"STALLWISE_TEST_PG is set but the app fell back to SQLite: "
                f"{db._last_db_error}"
            )
        client.fake_razorpay = _fake
        yield client


# --- Helpers that most tests need ---------------------------------------------
@pytest.fixture()
def make_seller(app_client):
    """Returns a factory that registers + verifies a seller and returns an
    authenticated request helper."""
    def _make(email=None, name="Test Seller", password="Passw0rd!"):
        email = email or f"seller_{uuid.uuid4().hex[:10]}@example.com"
        r = app_client.post("/api/auth/register",
                            json={"name": name, "email": email, "password": password})
        assert r.status_code == 200, r.text
        body = r.json()
        v = app_client.post("/api/auth/verify-otp",
                            json={"otp_id": body["otpId"], "otp": body["devOtp"]})
        assert v.status_code == 200, v.text
        token = v.json()["token"]

        class Seller:
            def __init__(self):
                self.email = email
                self.token = token
                self.headers = {"Authorization": f"Bearer {token}"}

            def get(self, path, **kw):
                return app_client.get(path, headers=self.headers, **kw)

            def post(self, path, **kw):
                return app_client.post(path, headers=self.headers, **kw)

            def put(self, path, **kw):
                return app_client.put(path, headers=self.headers, **kw)

            def delete(self, path, **kw):
                return app_client.delete(path, headers=self.headers, **kw)

        return Seller()

    return _make


@pytest.fixture()
def seller_with_store(make_seller):
    s = make_seller()
    slug = f"shop-{uuid.uuid4().hex[:8]}"
    r = s.post("/api/stores", json={"name": "Test Shop", "slug": slug, "bio": "Hand-made things."})
    assert r.status_code == 200, r.text
    s.store_slug = slug
    return s


def make_product(seller, **overrides):
    payload = {
        "title": "Widget",
        "description": "A fine widget.",
        "price": 250,
        "stock": 10,
        "active": True,
        "images": [],
        "optionGroups": [],
        "paymentMethods": ["online"],
    }
    payload.update(overrides)
    r = seller.post("/api/products", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def place_order(client, store_slug, items, payment_method="online",
                buyer=None):
    buyer = buyer or {}
    return client.post("/api/orders", json={
        "storeSlug": store_slug,
        "buyerName": buyer.get("name", "Bob Buyer"),
        "buyerEmail": buyer.get("email", "bob@example.com"),
        "buyerPhone": buyer.get("phone", "9876543210"),
        "paymentMethod": payment_method,
        "items": items,
    })
