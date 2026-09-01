"""What the buyer hears from us.

A buyer reaches a shop from a shared link, pays a stranger, and then finds out
whether this was a real business or a form that swallowed their money. Until
this file existed they heard nothing at all until dispatch — no receipt, no
order number, no way back to the order.

Brevo is never called: send_email is replaced, so these cover who gets told
what, not delivery.
"""
import asyncio

import pytest

import email_service
import server
from tests.conftest import make_product, place_order


@pytest.fixture()
def outbox(monkeypatch):
    """Captures every email the app tries to send."""
    sent = []

    async def capture(*, to, subject, html, recipient_name="User"):
        sent.append({"to": to, "subject": subject, "html": html, "name": recipient_name})
        return "fake-message-id"

    monkeypatch.setattr(email_service, "send_email", capture)
    return sent


async def _settle():
    """Emails go out on background tasks; let them run."""
    for _ in range(3):
        await asyncio.sleep(0)


def drain(app_client):
    """Run the pending email tasks the request left behind."""
    app_client.portal.call(_settle)


def to(outbox, address):
    return [m for m in outbox if m["to"] == address]


def test_the_buyer_gets_a_receipt_when_they_order(seller_with_store, app_client, outbox):
    product = make_product(seller_with_store, title="Brass Lamp", price=1200,
                           paymentMethods=["cod"])
    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": product["product_id"], "quantity": 2}],
                    payment_method="cod",
                    buyer={"name": "Priya", "email": "priya@example.com"})
    assert r.status_code == 200, r.text
    drain(app_client)

    receipts = to(outbox, "priya@example.com")
    assert len(receipts) == 1, "the buyer heard nothing"
    body = receipts[0]["html"]
    assert r.json()["orderId"] in body      # something to quote back to the seller
    assert "Brass Lamp" in body
    assert "Test Shop" in receipts[0]["subject"]
    assert "/order/" in body and "/orders/" not in body   # the public page, not the console


def test_the_receipt_says_cash_on_delivery_when_that_is_what_it_is(
        seller_with_store, app_client, outbox):
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "cod@example.com"})
    drain(app_client)

    body = to(outbox, "cod@example.com")[0]["html"]
    assert "To pay on delivery" in body
    assert "pay in cash when it arrives" in body


def test_the_seller_is_told_about_the_order_too(seller_with_store, app_client, outbox):
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    assert len(to(outbox, seller_with_store.email)) == 1
    assert "New order" in to(outbox, seller_with_store.email)[0]["subject"]


def test_a_seller_who_muted_alerts_still_lets_the_buyer_get_their_receipt(
        seller_with_store, app_client, outbox):
    """The seller's preference is about their own inbox, not the buyer's."""
    seller_with_store.put("/api/stores/me", json={"notifyNewOrder": False})
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    assert to(outbox, seller_with_store.email) == []
    assert len(to(outbox, "buyer@example.com")) == 1


def test_the_receipt_shows_the_delivery_charge(seller_with_store, app_client, outbox):
    seller_with_store.put("/api/stores/me", json={"deliveryFee": 60})
    product = make_product(seller_with_store, price=400, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    body = to(outbox, "buyer@example.com")[0]["html"]
    assert "Delivery" in body and "60.00" in body
    assert "460.00" in body       # what they actually owe


def test_free_delivery_is_shown_as_free(seller_with_store, app_client, outbox):
    seller_with_store.put("/api/stores/me", json={"deliveryFee": 60, "freeDeliveryAbove": 300})
    product = make_product(seller_with_store, price=400, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    body = to(outbox, "buyer@example.com")[0]["html"]
    assert "Free" in body


def test_a_failing_email_does_not_break_the_order(seller_with_store, app_client, monkeypatch):
    """Brevo being down must cost the buyer their receipt, not their order."""
    async def explode(**kwargs):
        raise RuntimeError("brevo is down")

    monkeypatch.setattr(email_service, "send_email", explode)
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": product["product_id"], "quantity": 1}],
                    payment_method="cod", buyer={"email": "buyer@example.com"})
    assert r.status_code == 200
    drain(app_client)
    # And the order is really there.
    assert seller_with_store.get("/api/orders").json()["orders"][0]["order_id"] == r.json()["orderId"]


def test_the_dispatch_code_still_goes_to_the_buyer(seller_with_store, app_client, outbox):
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    order = place_order(app_client, seller_with_store.store_slug,
                        [{"productId": product["product_id"], "quantity": 1}],
                        payment_method="cod", buyer={"email": "buyer@example.com"}).json()
    seller_with_store.post(f"/api/orders/{order['orderId']}/ship")
    drain(app_client)

    subjects = [m["subject"] for m in to(outbox, "buyer@example.com")]
    assert any("delivery code" in s for s in subjects)


# --- The links in those emails have to work ------------------------------
import re
from urllib.parse import urlparse, parse_qs


def only_link(html, needle):
    return re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)


def buyer_order_url(html):
    """The 'Track your order' link, as the buyer's mail client sees it."""
    links = [u for u in only_link(html, "/order/") if "/order/" in u]
    assert links, f"no buyer order link in the email: {links}"
    return links[0]


def test_the_buyers_link_opens_their_order(seller_with_store, app_client, outbox):
    """It used to point at /orders/<id>, which is the seller's console and
    behind a login — a wall between someone who just paid and their receipt."""
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    url = buyer_order_url(to(outbox, "buyer@example.com")[0]["html"])
    parsed = urlparse(url)
    assert parsed.path.startswith("/order/"), "the buyer was sent to the seller's page"

    # Follow it exactly as the buyer's browser would.
    r = app_client.get(f"/api{parsed.path}", params={
        "email": parse_qs(parsed.query).get("email", [""])[0]})
    assert r.status_code == 200, "the link in the receipt does not open the order"
    assert r.json()["buyerEmail"] == "buyer@example.com"


def test_a_link_without_the_email_is_useless_so_we_always_send_it(
        seller_with_store, app_client, outbox):
    """The page has no form to type an email into, so the link must carry it."""
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    url = buyer_order_url(to(outbox, "buyer@example.com")[0]["html"])
    assert "email=" in url
    # And without it the endpoint really does refuse, which is why it matters.
    assert app_client.get(f"/api/order/{urlparse(url).path.split('/')[-1]}").status_code == 404


def test_the_dispatch_email_link_works_too(seller_with_store, app_client, outbox):
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    order = place_order(app_client, seller_with_store.store_slug,
                        [{"productId": product["product_id"], "quantity": 1}],
                        payment_method="cod", buyer={"email": "buyer@example.com"}).json()
    seller_with_store.post(f"/api/orders/{order['orderId']}/ship")
    drain(app_client)

    dispatch = [m for m in to(outbox, "buyer@example.com")
                if "delivery code" in m["subject"]][0]
    parsed = urlparse(buyer_order_url(dispatch["html"]))
    r = app_client.get(f"/api{parsed.path}",
                       params={"email": parse_qs(parsed.query).get("email", [""])[0]})
    assert r.status_code == 200
    assert r.json()["otp"], "the buyer needs the delivery code on that page"


def test_the_sellers_link_goes_to_the_console(seller_with_store, app_client, outbox):
    product = make_product(seller_with_store, price=500, paymentMethods=["cod"])
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1}],
                payment_method="cod", buyer={"email": "buyer@example.com"})
    drain(app_client)

    html = to(outbox, seller_with_store.email)[0]["html"]
    assert any("/orders/" in u for u in only_link(html, "/orders/"))
    # And the seller's own link must not leak the buyer's email into a URL.
    assert "email=" not in html
