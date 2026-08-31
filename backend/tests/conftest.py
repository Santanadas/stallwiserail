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
             "SENDINBLUE_API_KEY", "RAZORPAY_WEBHOOK_SECRET"):
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


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """A TestClient bound to a fresh SQLite database."""
    import db
    import route_service
    import security
    import server

    # The sliding-window rate limiter is process-global in-memory state, so it
    # leaks between tests and eventually 429s the whole suite. Reset it.
    security._rate_limits.clear()

    # Fresh, isolated database + upload dir for this test.
    monkeypatch.setattr(db, "DB_FILE", tmp_path / "test.db", raising=False)
    monkeypatch.setattr(db, "_sqlite_conn", None, raising=False)
    monkeypatch.setattr(db, "_pool", None, raising=False)
    monkeypatch.setattr(db, "_ENGINE", "sqlite", raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    # Never touch the real Razorpay API.
    _fake = FakeRazorpay()
    monkeypatch.setattr(route_service, "platform_client",
                        lambda: (_fake, "rzp_test_fake", PLATFORM_SECRET))
    monkeypatch.setattr("razorpay.Client", FakeRazorpay)

    from fastapi.testclient import TestClient

    with TestClient(server.app) as client:
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
