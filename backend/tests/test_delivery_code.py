"""Handing the parcel over.

The seller reads a six-digit code off the buyer's phone at the door. Five wrong
entries used to lock it permanently, with no unlock and no resend, so the order
stayed "shipped" for ever — never delivered, never completed, and for cash on
delivery never even marked paid. Neither side was told what to do about it.
"""
import asyncio

import pytest

import email_service
import server
from tests.conftest import make_product, place_order


@pytest.fixture()
def outbox(monkeypatch):
    sent = []

    async def capture(*, to, subject, html, recipient_name="User"):
        sent.append({"to": to, "subject": subject, "html": html})
        return "id"

    monkeypatch.setattr(email_service, "send_email", capture)
    return sent


async def _settle():
    for _ in range(3):
        await asyncio.sleep(0)


def drain(app_client):
    app_client.portal.call(_settle)


def shipped_order(app_client, seller):
    product = make_product(seller, price=500, paymentMethods=["cod"])
    order = place_order(app_client, seller.store_slug,
                        [{"productId": product["product_id"], "quantity": 1}],
                        payment_method="cod",
                        buyer={"email": "buyer@example.com"}).json()
    assert seller.post(f"/api/orders/{order['orderId']}/ship").status_code == 200
    return order["orderId"]


def code_for(app_client, order_id):
    """The code as the buyer sees it on their order page."""
    return app_client.get(f"/api/order/{order_id}",
                          params={"email": "buyer@example.com"}).json()["otp"]


def wrong_code(app_client, seller, order_id, times):
    last = None
    for _ in range(times):
        last = seller.post(f"/api/orders/{order_id}/confirm-delivery", json={"otp": "000000"})
    return last


def test_the_right_code_completes_the_handover(app_client, seller_with_store):
    order_id = shipped_order(app_client, seller_with_store)
    r = seller_with_store.post(f"/api/orders/{order_id}/confirm-delivery",
                               json={"otp": code_for(app_client, order_id)})
    assert r.status_code == 200
    assert r.json()["status"] == "delivered"


def test_too_many_wrong_entries_lock_the_code(app_client, seller_with_store):
    order_id = shipped_order(app_client, seller_with_store)
    last = wrong_code(app_client, seller_with_store, order_id, server.OTP_MAX_ATTEMPTS)
    assert last.status_code == 423
    assert seller_with_store.get(f"/api/orders/{order_id}").json()["otpLocked"] is True


def test_a_locked_order_is_not_a_dead_end(app_client, seller_with_store, outbox):
    """The bug: nothing could unlock it, so the order was stranded for good."""
    order_id = shipped_order(app_client, seller_with_store)
    wrong_code(app_client, seller_with_store, order_id, server.OTP_MAX_ATTEMPTS)

    r = seller_with_store.post(f"/api/orders/{order_id}/resend-code")
    assert r.status_code == 200
    assert seller_with_store.get(f"/api/orders/{order_id}").json()["otpLocked"] is False

    fresh = code_for(app_client, order_id)
    done = seller_with_store.post(f"/api/orders/{order_id}/confirm-delivery", json={"otp": fresh})
    assert done.status_code == 200
    assert done.json()["status"] == "delivered"


def test_the_locked_message_says_what_to_do(app_client, seller_with_store):
    order_id = shipped_order(app_client, seller_with_store)
    last = wrong_code(app_client, seller_with_store, order_id, server.OTP_MAX_ATTEMPTS)
    assert "new code" in last.json()["detail"]

    stuck = seller_with_store.post(f"/api/orders/{order_id}/confirm-delivery", json={"otp": "111111"})
    assert stuck.status_code == 423
    assert "new one" in stuck.json()["detail"]


def test_resending_replaces_the_old_code(app_client, seller_with_store):
    """A resend must not leave the previous code working."""
    order_id = shipped_order(app_client, seller_with_store)
    old = code_for(app_client, order_id)
    seller_with_store.post(f"/api/orders/{order_id}/resend-code")
    new = code_for(app_client, order_id)
    assert new != old

    assert seller_with_store.post(f"/api/orders/{order_id}/confirm-delivery",
                                  json={"otp": old}).status_code == 400
    assert seller_with_store.post(f"/api/orders/{order_id}/confirm-delivery",
                                  json={"otp": new}).status_code == 200


def test_the_new_code_reaches_the_buyer(app_client, seller_with_store, outbox):
    order_id = shipped_order(app_client, seller_with_store)
    outbox.clear()
    seller_with_store.post(f"/api/orders/{order_id}/resend-code")
    drain(app_client)

    sent = [m for m in outbox if m["to"] == "buyer@example.com"]
    assert len(sent) == 1
    assert code_for(app_client, order_id) in sent[0]["html"]


def test_a_resend_does_not_reveal_the_code_to_the_caller(app_client, seller_with_store):
    order_id = shipped_order(app_client, seller_with_store)
    body = seller_with_store.post(f"/api/orders/{order_id}/resend-code").json()
    assert body == {"ok": True}


def test_only_the_owner_can_resend(app_client, seller_with_store, make_seller):
    order_id = shipped_order(app_client, seller_with_store)
    intruder = make_seller()
    assert intruder.post(f"/api/orders/{order_id}/resend-code").status_code == 404
    assert app_client.post(f"/api/orders/{order_id}/resend-code").status_code == 401


def test_an_undispatched_order_has_no_code_to_resend(app_client, seller_with_store):
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    order = place_order(app_client, seller_with_store.store_slug,
                        [{"productId": product["product_id"], "quantity": 1}],
                        payment_method="cod").json()
    r = seller_with_store.post(f"/api/orders/{order['orderId']}/resend-code")
    assert r.status_code == 400


def test_resends_are_rate_limited(app_client, seller_with_store):
    """Otherwise it is a way to flood the buyer's inbox."""
    order_id = shipped_order(app_client, seller_with_store)
    codes = [seller_with_store.post(f"/api/orders/{order_id}/resend-code").status_code
             for _ in range(12)]
    assert 429 in codes
