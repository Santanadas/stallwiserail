"""Stock held by unpaid checkouts, and who gets told when money moves.

Stock is taken at checkout so two buyers cannot take the last one. Nothing ever
gave it back, so every closed payment window quietly removed a unit from the
shop for good — a seller with ten in stock could reach zero without selling
anything and see only a listing that had stopped selling.
"""
import asyncio
import json

import pytest

import email_service
import server
from tests.conftest import (PLATFORM_SECRET, make_product, place_order,
                            razorpay_signature, webhook_signature)


@pytest.fixture()
def outbox(monkeypatch):
    sent = []

    async def capture(*, to, subject, html, recipient_name="User"):
        sent.append({"to": to, "subject": subject, "html": html})
        return "fake-id"

    monkeypatch.setattr(email_service, "send_email", capture)
    return sent


async def _settle():
    for _ in range(3):
        await asyncio.sleep(0)


def drain(app_client):
    app_client.portal.call(_settle)


def stock_of(seller, product_id):
    return [p for p in seller.get("/api/products").json()
            if p["product_id"] == product_id][0]["stock"]


def start_checkout(app_client, seller, product, qty=1):
    return place_order(app_client, seller.store_slug,
                       [{"productId": product["product_id"], "quantity": qty,
                         "optionSelections": {}}],
                       buyer={"email": "buyer@example.com"}).json()


def age_order(app_client, order_id, minutes=90):
    """Push an order back in time so the sweeper sees it as abandoned."""
    from datetime import timedelta
    import db

    stamp = server.iso(server.now() - timedelta(minutes=minutes))
    app_client.portal.call(
        db.execute, "UPDATE orders SET created_at = $1 WHERE order_id = $2",
        stamp, order_id)


def sweep(app_client):
    return app_client.portal.call(server.release_abandoned_checkouts)


# --- The leak ------------------------------------------------------------
def test_checkout_holds_stock(app_client, seller_with_store):
    product = make_product(seller_with_store, stock=10)
    start_checkout(app_client, seller_with_store, product, qty=3)
    assert stock_of(seller_with_store, product["product_id"]) == 7


def test_an_abandoned_checkout_gives_the_stock_back(app_client, seller_with_store):
    """The bug: a buyer who closes the payment window used to cost the seller a
    unit of stock permanently."""
    product = make_product(seller_with_store, stock=10)
    order = start_checkout(app_client, seller_with_store, product, qty=3)
    assert stock_of(seller_with_store, product["product_id"]) == 7

    age_order(app_client, order["orderId"])
    assert sweep(app_client) == 1

    assert stock_of(seller_with_store, product["product_id"]) == 10
    assert seller_with_store.get(f"/api/orders/{order['orderId']}").json()["status"] == "abandoned"


def test_a_recent_checkout_is_left_alone(app_client, seller_with_store):
    """A buyer still typing their card number must not lose the item."""
    product = make_product(seller_with_store, stock=5)
    start_checkout(app_client, seller_with_store, product, qty=2)
    assert sweep(app_client) == 0
    assert stock_of(seller_with_store, product["product_id"]) == 3


def test_a_paid_order_is_never_swept(app_client, seller_with_store):
    product = make_product(seller_with_store, stock=5)
    order = start_checkout(app_client, seller_with_store, product, qty=2)
    rp, pay = order["razorpayOrderId"], "pay_ok"
    app_client.post(f"/api/orders/{order['orderId']}/verify-payment", json={
        "razorpay_order_id": rp, "razorpay_payment_id": pay,
        "razorpay_signature": razorpay_signature(rp, pay)})

    age_order(app_client, order["orderId"])
    assert sweep(app_client) == 0
    assert stock_of(seller_with_store, product["product_id"]) == 3


def test_cod_orders_are_never_swept(app_client, seller_with_store):
    """Nothing is pending for a COD order — it is already a real sale."""
    product = make_product(seller_with_store, stock=5, paymentMethods=["cod"])
    order = place_order(app_client, seller_with_store.store_slug,
                        [{"productId": product["product_id"], "quantity": 2}],
                        payment_method="cod").json()
    age_order(app_client, order["orderId"])
    assert sweep(app_client) == 0
    assert stock_of(seller_with_store, product["product_id"]) == 3


def test_sweeping_twice_does_not_invent_stock(app_client, seller_with_store):
    product = make_product(seller_with_store, stock=5)
    order = start_checkout(app_client, seller_with_store, product, qty=2)
    age_order(app_client, order["orderId"])

    assert sweep(app_client) == 1
    assert sweep(app_client) == 0
    assert stock_of(seller_with_store, product["product_id"]) == 5


def test_paying_after_the_sweep_still_works(app_client, seller_with_store):
    """A late payment must become a real sale, and take its stock back."""
    product = make_product(seller_with_store, stock=5)
    order = start_checkout(app_client, seller_with_store, product, qty=2)
    age_order(app_client, order["orderId"])
    sweep(app_client)
    assert stock_of(seller_with_store, product["product_id"]) == 5

    rp, pay = order["razorpayOrderId"], "pay_late"
    r = app_client.post(f"/api/orders/{order['orderId']}/verify-payment", json={
        "razorpay_order_id": rp, "razorpay_payment_id": pay,
        "razorpay_signature": razorpay_signature(rp, pay)})
    assert r.status_code == 200
    assert r.json()["status"] == "paid"
    assert stock_of(seller_with_store, product["product_id"]) == 3


# --- Who gets told, and when ---------------------------------------------
def test_nobody_is_emailed_before_the_buyer_pays(app_client, seller_with_store, outbox):
    """Reaching the payment screen is not an order. A receipt saying "Paid" for
    money that was never taken is worse than no receipt at all."""
    product = make_product(seller_with_store)
    start_checkout(app_client, seller_with_store, product)
    drain(app_client)
    assert outbox == []


def test_paying_sends_the_buyer_a_receipt_and_the_seller_an_alert(
        app_client, seller_with_store, outbox):
    product = make_product(seller_with_store, title="Clay Pot")
    order = start_checkout(app_client, seller_with_store, product)
    rp, pay = order["razorpayOrderId"], "pay_ok"
    app_client.post(f"/api/orders/{order['orderId']}/verify-payment", json={
        "razorpay_order_id": rp, "razorpay_payment_id": pay,
        "razorpay_signature": razorpay_signature(rp, pay)})
    drain(app_client)

    buyer = [m for m in outbox if m["to"] == "buyer@example.com"]
    seller = [m for m in outbox if m["to"] == seller_with_store.email]
    assert len(buyer) == 1
    assert "Clay Pot" in buyer[0]["html"]
    assert "Paid" in buyer[0]["html"]
    assert len(seller) >= 1


def test_the_buyer_is_not_sent_two_receipts(app_client, seller_with_store, outbox):
    """The browser callback and the webhook can both report the same payment."""
    product = make_product(seller_with_store)
    order = start_checkout(app_client, seller_with_store, product)
    rp, pay = order["razorpayOrderId"], "pay_ok"
    payload = {"razorpay_order_id": rp, "razorpay_payment_id": pay,
               "razorpay_signature": razorpay_signature(rp, pay)}
    app_client.post(f"/api/orders/{order['orderId']}/verify-payment", json=payload)
    app_client.post(f"/api/orders/{order['orderId']}/verify-payment", json=payload)
    drain(app_client)

    assert len([m for m in outbox if m["to"] == "buyer@example.com"]) == 1


def test_a_payment_seen_only_by_the_webhook_still_tells_everyone(
        app_client, seller_with_store, outbox, monkeypatch):
    """On mobile the browser often never returns from Razorpay, so the webhook
    is the only witness. It used to mark the row paid and email nobody."""
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "hookhook")
    product = make_product(seller_with_store, title="Jute Bag")
    order = start_checkout(app_client, seller_with_store, product)

    body = json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_hook",
                                           "order_id": order["razorpayOrderId"]}}},
    }).encode()
    r = app_client.post("/api/webhooks/razorpay", content=body,
                        headers={"X-Razorpay-Signature": webhook_signature(body, "hookhook"),
                                 "Content-Type": "application/json"})
    assert r.status_code == 200
    drain(app_client)

    assert seller_with_store.get(f"/api/orders/{order['orderId']}").json()["status"] == "paid"
    buyer = [m for m in outbox if m["to"] == "buyer@example.com"]
    assert len(buyer) == 1, "the buyer paid and heard nothing"
    assert "Jute Bag" in buyer[0]["html"]
    assert [m for m in outbox if m["to"] == seller_with_store.email]


def test_the_webhook_and_the_callback_together_send_one_receipt(
        app_client, seller_with_store, outbox, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "hookhook")
    product = make_product(seller_with_store)
    order = start_checkout(app_client, seller_with_store, product)

    body = json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_hook",
                                           "order_id": order["razorpayOrderId"]}}},
    }).encode()
    app_client.post("/api/webhooks/razorpay", content=body,
                    headers={"X-Razorpay-Signature": webhook_signature(body, "hookhook"),
                             "Content-Type": "application/json"})
    rp, pay = order["razorpayOrderId"], "pay_hook"
    app_client.post(f"/api/orders/{order['orderId']}/verify-payment", json={
        "razorpay_order_id": rp, "razorpay_payment_id": pay,
        "razorpay_signature": razorpay_signature(rp, pay)})
    drain(app_client)

    assert len([m for m in outbox if m["to"] == "buyer@example.com"]) == 1
