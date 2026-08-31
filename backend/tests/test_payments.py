import json

from conftest import (PLATFORM_SECRET, make_product, place_order,
                      razorpay_signature, webhook_signature)


def _online_order(app_client, seller, price=400):
    p = make_product(seller, price=price)
    r = place_order(app_client, seller.store_slug,
                    [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}])
    return r.json()


# ------------------------------------------------- buyer payment verification
def test_valid_signature_marks_order_paid(app_client, seller_with_store):
    o = _online_order(app_client, seller_with_store)
    rp_order, pay_id = o["razorpayOrderId"], "pay_test_123"
    r = app_client.post(f"/api/orders/{o['orderId']}/verify-payment", json={
        "razorpay_order_id": rp_order,
        "razorpay_payment_id": pay_id,
        "razorpay_signature": razorpay_signature(rp_order, pay_id),
    })
    assert r.status_code == 200
    assert r.json()["status"] == "paid"
    assert seller_with_store.get(f"/api/orders/{o['orderId']}").json()["paidAt"]


def test_forged_signature_is_rejected(app_client, seller_with_store):
    o = _online_order(app_client, seller_with_store)
    r = app_client.post(f"/api/orders/{o['orderId']}/verify-payment", json={
        "razorpay_order_id": o["razorpayOrderId"],
        "razorpay_payment_id": "pay_forged",
        "razorpay_signature": "deadbeef" * 8,
    })
    assert r.status_code == 400
    assert "signature" in r.json()["detail"].lower()
    assert seller_with_store.get(f"/api/orders/{o['orderId']}").json()["status"] == "placed"


def test_signature_from_a_different_order_is_rejected(app_client, seller_with_store):
    a = _online_order(app_client, seller_with_store)
    b = _online_order(app_client, seller_with_store)
    # A perfectly valid signature, but for order B — must not pay off order A.
    r = app_client.post(f"/api/orders/{a['orderId']}/verify-payment", json={
        "razorpay_order_id": b["razorpayOrderId"],
        "razorpay_payment_id": "pay_x",
        "razorpay_signature": razorpay_signature(b["razorpayOrderId"], "pay_x"),
    })
    assert r.status_code == 400
    assert seller_with_store.get(f"/api/orders/{a['orderId']}").json()["status"] == "placed"


def test_verify_payment_is_idempotent(app_client, seller_with_store):
    o = _online_order(app_client, seller_with_store)
    payload = {
        "razorpay_order_id": o["razorpayOrderId"],
        "razorpay_payment_id": "pay_once",
        "razorpay_signature": razorpay_signature(o["razorpayOrderId"], "pay_once"),
    }
    first = app_client.post(f"/api/orders/{o['orderId']}/verify-payment", json=payload)
    second = app_client.post(f"/api/orders/{o['orderId']}/verify-payment", json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert second.json()["status"] == "paid"


# ------------------------------------------------------------------ webhooks
def test_webhook_marks_order_paid(app_client, seller_with_store):
    o = _online_order(app_client, seller_with_store)
    body = {"event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_hook", "order_id": o["razorpayOrderId"]}}}}
    r = app_client.post("/api/webhooks/razorpay", json=body)
    assert r.status_code == 200
    assert seller_with_store.get(f"/api/orders/{o['orderId']}").json()["status"] == "paid"


def test_webhook_signature_enforced_when_secret_is_set(app_client, seller_with_store, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "hook-secret")
    o = _online_order(app_client, seller_with_store)
    body = {"event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "p", "order_id": o["razorpayOrderId"]}}}}
    raw = json.dumps(body).encode()

    bad = app_client.post("/api/webhooks/razorpay", content=raw,
                          headers={"Content-Type": "application/json",
                                   "X-Razorpay-Signature": "nope"})
    assert bad.status_code == 400
    assert seller_with_store.get(f"/api/orders/{o['orderId']}").json()["status"] == "placed"

    good = app_client.post("/api/webhooks/razorpay", content=raw,
                           headers={"Content-Type": "application/json",
                                    "X-Razorpay-Signature": webhook_signature(raw, "hook-secret")})
    assert good.status_code == 200
    assert seller_with_store.get(f"/api/orders/{o['orderId']}").json()["status"] == "paid"


def test_webhook_ignores_unrelated_events(app_client, seller_with_store):
    o = _online_order(app_client, seller_with_store)
    app_client.post("/api/webhooks/razorpay", json={
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": "p", "order_id": o["razorpayOrderId"]}}}})
    assert seller_with_store.get(f"/api/orders/{o['orderId']}").json()["status"] == "placed"


# -------------------------------------------------------------- subscriptions
def test_subscription_defaults_to_free_plan(seller_with_store):
    sub = seller_with_store.get("/api/subscription").json()
    assert sub["subscriptionStatus"] == "inactive"
    assert sub["commissionRate"] == 0.10
    assert sub["plans"] == {"monthly": 199, "yearly": 1499}


def test_subscription_create_and_verify_activates_pro(seller_with_store):
    created = seller_with_store.post("/api/subscription/create", json={"interval": "yearly"})
    assert created.status_code == 200, created.text
    order_id = created.json()["orderId"]

    r = seller_with_store.post("/api/subscription/verify-payment", json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_sub",
        "razorpay_signature": razorpay_signature(order_id, "pay_sub"),
    })
    assert r.status_code == 200
    assert r.json()["subscriptionStatus"] == "active"
    assert seller_with_store.get("/api/subscription").json()["subscriptionStatus"] == "active"


def test_subscription_forged_signature_rejected(seller_with_store):
    order_id = seller_with_store.post("/api/subscription/create",
                                      json={"interval": "monthly"}).json()["orderId"]
    r = seller_with_store.post("/api/subscription/verify-payment", json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_sub",
        "razorpay_signature": "0" * 64,
    })
    assert r.status_code == 400
    assert seller_with_store.get("/api/subscription").json()["subscriptionStatus"] == "inactive"


def test_subscription_rejects_bad_interval(seller_with_store):
    assert seller_with_store.post("/api/subscription/create",
                                  json={"interval": "weekly"}).status_code == 400


def test_subscription_requires_auth(app_client):
    assert app_client.get("/api/subscription").status_code == 401
