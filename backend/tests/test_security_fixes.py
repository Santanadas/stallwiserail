"""Regressions for the vulnerabilities and money bugs found in the audit.

Each test names the defect it guards, because none of these are obvious from
reading the endpoint they cover.
"""
import time

import pytest

import route_service
import security
import server
from tests.conftest import make_product, place_order, raw_fetch_one


# --- 1. Authentication bypass via the abandoned Emergent session endpoint ---
def test_emergent_google_session_endpoint_is_gone(app_client):
    """It took a session_id, asked demobackend.emergentagent.com whose it was,
    and logged in as whatever email came back — creating the account if it did
    not exist. Anyone who could make that third party answer with a chosen
    address owned the matching Stall Wise account."""
    r = app_client.post("/api/auth/google/session", json={"session_id": "anything"})
    # 405: the SPA catch-all owns the path now and serves GET only. What matters
    # is that no session is ever issued.
    assert r.status_code in (404, 405)
    assert "token" not in r.text


def test_no_code_path_still_trusts_the_demo_backend():
    import inspect
    src = inspect.getsource(server)
    assert "demobackend.emergentagent.com" not in src
    assert "GoogleSessionIn" not in src


# --- 2. Razorpay calls could hang forever -----------------------------------
def test_razorpay_client_always_carries_a_timeout():
    """The SDK never passes a timeout to requests, and it retries. Hung calls
    hold threads in the default executor that asyncio.to_thread draws from;
    exhaust it and image serving and SQLite queries stall too — which is how a
    slow payment call takes the whole origin down."""
    c = route_service.razorpay_client("k", "s")
    assert type(c.session).__name__ == "_TimeoutSession"
    assert c.max_retries == 1
    assert 0 < route_service.RAZORPAY_TIMEOUT <= 30

    # The session must inject a timeout even when the caller passes none.
    captured = {}
    import requests
    real = requests.Session.request

    def spy(self, *a, **kw):
        captured.update(kw)
        raise RuntimeError("stop before the network")

    requests.Session.request = spy
    try:
        with pytest.raises(RuntimeError):
            c.session.request("GET", "https://example.invalid")
    finally:
        requests.Session.request = real
    assert captured.get("timeout") == route_service.RAZORPAY_TIMEOUT


def test_every_client_is_built_through_the_bounded_helper():
    import inspect
    assert "razorpay.Client(" not in inspect.getsource(server)


# --- 3. Delivery charges were configured but never billed -------------------
def test_delivery_charge_is_actually_added_to_the_order(app_client, seller_with_store):
    """The shop's delivery fee was stored and shown in Settings but never
    applied — _record_order hardcoded 0 and billed the subtotal."""
    seller_with_store.put("/api/stores/me", json={"deliveryFee": 60})
    p = make_product(seller_with_store, price=500, stock=10, paymentMethods=["online", "cod"])

    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}],
                    payment_method="cod")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subtotal"] == 500
    assert body["deliveryFee"] == 60
    assert body["amount"] == 560

    row = raw_fetch_one("SELECT subtotal, delivery_fee, amount FROM orders WHERE order_id = $1",
                        body["orderId"])
    assert float(row["subtotal"]) == 500
    assert float(row["delivery_fee"]) == 60
    assert float(row["amount"]) == 560


def test_free_delivery_threshold_is_inclusive(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me",
                          json={"deliveryFee": 60, "freeDeliveryAbove": 1000})
    p = make_product(seller_with_store, price=500, stock=10, paymentMethods=["online", "cod"])

    def order(qty):
        return place_order(app_client, seller_with_store.store_slug,
                           [{"productId": p["product_id"], "quantity": qty, "optionSelections": {}}],
                           payment_method="cod").json()

    assert order(1)["deliveryFee"] == 60      # ₹500, under the threshold
    assert order(2)["deliveryFee"] == 0       # ₹1000, exactly at it — free


def test_no_delivery_fee_when_the_shop_has_not_set_one(app_client, seller_with_store):
    p = make_product(seller_with_store, price=500, stock=10, paymentMethods=["online", "cod"])
    body = place_order(app_client, seller_with_store.store_slug,
                       [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}],
                       payment_method="cod").json()
    assert body["deliveryFee"] == 0 and body["amount"] == 500


def test_delivery_helper_edge_cases():
    assert server.delivery_for({}, 100) == 0
    assert server.delivery_for({"delivery_fee": 0}, 100) == 0
    assert server.delivery_for({"delivery_fee": 60}, 100) == 60
    assert server.delivery_for({"delivery_fee": 60, "free_delivery_above": None}, 10_000) == 60
    assert server.delivery_for({"delivery_fee": 60, "free_delivery_above": 500}, 499.99) == 60
    assert server.delivery_for({"delivery_fee": 60, "free_delivery_above": 500}, 500) == 0


# --- 4. Endpoints that had no rate limit ------------------------------------
def _exhaust(key_prefix, limit):
    """Fill the sliding window so the next real request is rejected."""
    for _ in range(limit + 1):
        security.check_rate_limit(key_prefix, max_requests=limit, window_seconds=600)


def test_buyer_order_lookup_is_rate_limited(app_client, monkeypatch):
    """The response carries the buyer's name, phone, address and delivery code.
    Unlimited requests let an order id be paired against guessed emails."""
    monkeypatch.setattr(security, "check_rate_limit", lambda *a, **k: False)
    r = app_client.get("/api/order/order_whatever", params={"email": "a@b.com"})
    assert r.status_code == 429


def test_password_reset_is_rate_limited(app_client, monkeypatch):
    monkeypatch.setattr(security, "check_rate_limit", lambda *a, **k: False)
    r = app_client.post("/api/auth/reset-password",
                        json={"token": "x" * 40, "password": "Passw0rd!"})
    assert r.status_code == 429


def test_dispute_is_rate_limited(app_client, monkeypatch):
    monkeypatch.setattr(security, "check_rate_limit", lambda *a, **k: False)
    r = app_client.post("/api/order/order_whatever/dispute",
                        json={"email": "a@b.com", "reason": "not delivered"})
    assert r.status_code == 429


def test_dashboard_summary_is_rate_limited(seller_with_store, monkeypatch):
    """It reads up to 2000 orders and aggregates them in Python — the most
    expensive authenticated call in the app."""
    monkeypatch.setattr(security, "check_rate_limit", lambda *a, **k: False)
    assert seller_with_store.get("/api/dashboard/summary").status_code == 429


def test_rate_limiter_actually_closes_the_window():
    security._rate_limits.clear()
    key = "unit-test-window"
    assert all(security.check_rate_limit(key, 3, 600) for _ in range(3))
    assert security.check_rate_limit(key, 3, 600) is False


# --- 5. Gateway errors must not leak to the client --------------------------
def test_rejected_razorpay_credentials_are_reported_as_a_platform_outage(seller_with_store, monkeypatch):
    """Razorpay answers "Authentication failed" when the key pair is rejected.
    That is a deployment misconfiguration — and because the same keys back every
    buyer checkout, it means payments are down shopwide, not just billing."""
    import razorpay
    import server as srv

    monkeypatch.setattr(srv, "_RP_KEY_ID", "rzp_live_x")
    monkeypatch.setattr(srv, "_RP_KEY_SECRET", "wrong")

    def boom(*a, **k):
        raise razorpay.errors.BadRequestError("Authentication failed")

    class _C:
        order = type("O", (), {"create": staticmethod(boom)})()

    monkeypatch.setattr(srv.route_service, "razorpay_client", lambda *a, **k: _C())

    r = seller_with_store.post("/api/subscription/create", json={"interval": "monthly"})
    assert r.status_code == 503
    body = r.json()["detail"]
    assert "temporarily unavailable" in body
    # The gateway's own wording must not reach the browser.
    assert "Authentication failed" not in body
    assert "razorpay" not in body.lower()


def test_other_gateway_errors_do_not_leak_their_message(seller_with_store, monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, "_RP_KEY_ID", "rzp_live_x")
    monkeypatch.setattr(srv, "_RP_KEY_SECRET", "s")

    def boom(*a, **k):
        raise RuntimeError("internal detail nobody outside should read")

    class _C:
        order = type("O", (), {"create": staticmethod(boom)})()

    monkeypatch.setattr(srv.route_service, "razorpay_client", lambda *a, **k: _C())

    r = seller_with_store.post("/api/subscription/create", json={"interval": "monthly"})
    assert r.status_code == 502
    assert "internal detail" not in r.json()["detail"]
