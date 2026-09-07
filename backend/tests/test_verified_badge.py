"""The verified badge.

Earned by carrying 50 orders all the way through to completed — not by
subscribing. A badge a seller can buy tells a buyer nothing except that
somebody paid, which is worse than no badge at all: it spends the trust the
honest sellers built.
"""
import uuid

import pytest

import server
from tests.conftest import make_product, place_order, raw_execute


def complete_orders(app_client, seller, n, status="completed"):
    """Put n finished orders on this seller's books.

    Written straight to the table rather than driven through checkout: fifty
    real checkouts trip the per-IP order rate limit, and what is under test
    here is the count, not the checkout.
    """
    store = seller.get("/api/stores/me").json()
    for i in range(n):
        raw_execute(
            """
            INSERT INTO orders (order_id, seller_id, store_slug, buyer_name,
                buyer_email, buyer_phone, subtotal, amount, status,
                payment_method, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            f"ord_v{i}_{uuid.uuid4().hex[:8]}", store["sellerId"], store["slug"],
            "Bob Buyer", f"bob{i}@example.com", "9876543210",
            100.0, 100.0, status, "cod", "2026-01-01T00:00:00+00:00")


def badge(app_client, seller):
    return app_client.get(f"/api/shop/{seller.store_slug}").json()["verified"]


# --- Earning it ----------------------------------------------------------
def test_a_new_shop_is_not_verified(app_client, seller_with_store):
    make_product(seller_with_store)
    assert badge(app_client, seller_with_store) is False


def test_one_short_is_still_not_verified(app_client, seller_with_store):
    complete_orders(app_client, seller_with_store, server.VERIFIED_AFTER_ORDERS - 1)
    assert badge(app_client, seller_with_store) is False


def test_the_fiftieth_completed_order_earns_it(app_client, seller_with_store):
    complete_orders(app_client, seller_with_store, server.VERIFIED_AFTER_ORDERS)
    assert badge(app_client, seller_with_store) is True


# --- What does not count -------------------------------------------------
@pytest.mark.parametrize("status", ["placed", "paid", "shipped", "delivered",
                                    "disputed", "abandoned"])
def test_only_completed_orders_count(app_client, seller_with_store, status):
    """An order still in flight, or disputed, has not proved anything yet.
    'delivered' is deliberately excluded: its acceptance window is still open,
    so the buyer can still raise a dispute."""
    complete_orders(app_client, seller_with_store, server.VERIFIED_AFTER_ORDERS,
                    status=status)
    assert badge(app_client, seller_with_store) is False


def test_paying_for_pro_does_not_buy_the_badge(app_client, seller_with_store):
    """The marketing has historically offered a "Verified Pro Seller Badge".
    Whatever the plan says, this badge is not for sale."""
    raw_execute("UPDATE users SET subscription_status = 'active' WHERE user_id = $1",
                seller_with_store.get("/api/stores/me").json()["sellerId"])
    assert seller_with_store.get("/api/subscription").json()["subscriptionStatus"] == "active"
    assert badge(app_client, seller_with_store) is False


def test_another_sellers_orders_do_not_count(app_client, seller_with_store, make_seller):
    other = make_seller()
    other.post("/api/stores", json={"name": "Other", "slug": "other-verified", "bio": ""})
    other.store_slug = "other-verified"
    complete_orders(app_client, other, server.VERIFIED_AFTER_ORDERS)

    make_product(seller_with_store)
    assert badge(app_client, seller_with_store) is False
    assert badge(app_client, other) is True


# --- Where it shows ------------------------------------------------------
def test_the_product_page_carries_it_too(app_client, seller_with_store):
    complete_orders(app_client, seller_with_store, server.VERIFIED_AFTER_ORDERS)
    product = make_product(seller_with_store, title="Signed Piece")
    body = app_client.get(
        f"/api/shop/{seller_with_store.store_slug}/product/{product['slug']}").json()
    assert body["verified"] is True


def test_the_public_view_does_not_publish_the_order_count(app_client, seller_with_store):
    """A buyer's trust signal, not the seller's turnover."""
    complete_orders(app_client, seller_with_store, server.VERIFIED_AFTER_ORDERS)
    shop = app_client.get(f"/api/shop/{seller_with_store.store_slug}").json()
    assert shop["verified"] is True
    assert "completedOrders" not in str(shop)


# --- The seller can see it coming ----------------------------------------
def test_the_seller_sees_their_own_progress(app_client, seller_with_store):
    complete_orders(app_client, seller_with_store, 3)
    v = seller_with_store.get("/api/dashboard/summary").json()["verification"]
    assert v == {"completedOrders": 3, "required": server.VERIFIED_AFTER_ORDERS,
                 "verified": False}


def test_progress_reaches_verified(app_client, seller_with_store):
    complete_orders(app_client, seller_with_store, server.VERIFIED_AFTER_ORDERS)
    v = seller_with_store.get("/api/dashboard/summary").json()["verification"]
    assert v["verified"] is True
    assert v["completedOrders"] == server.VERIFIED_AFTER_ORDERS
