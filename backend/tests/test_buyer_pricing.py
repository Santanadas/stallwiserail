"""What the buyer is quoted has to be what the buyer is charged.

The cart used to show the item subtotal and call it "Total", while the payment
window asked for subtotal plus delivery. A first-time buyer seeing ₹400 in the
cart and ₹460 in the Razorpay popup has just been given a reason not to trust
the site — and for cash on delivery there was no popup at all, so they only
found out when the parcel arrived.
"""
from tests.conftest import make_product, place_order


def shop(app_client, seller):
    return app_client.get(f"/api/shop/{seller.store_slug}").json()


def test_the_shop_page_publishes_the_delivery_terms(app_client, seller_with_store):
    """The buyer's cart cannot quote a total it is not told the rules for."""
    seller_with_store.put("/api/stores/me",
                          json={"deliveryFee": 60, "freeDeliveryAbove": 999, "dispatchDays": 3})
    make_product(seller_with_store, price=400)

    store = shop(app_client, seller_with_store)["store"]
    assert store["deliveryFee"] == 60.0
    assert store["freeDeliveryAbove"] == 999.0
    assert store["dispatchDays"] == 3


def test_the_product_page_publishes_them_too(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me", json={"deliveryFee": 40})
    product = make_product(seller_with_store, price=400)
    slug = product["slug"]

    store = app_client.get(
        f"/api/shop/{seller_with_store.store_slug}/product/{slug}").json()["store"]
    assert store["deliveryFee"] == 40.0


def test_a_shop_with_no_delivery_charge_says_zero(app_client, seller_with_store):
    make_product(seller_with_store, price=400)
    store = shop(app_client, seller_with_store)["store"]
    assert store["deliveryFee"] == 0.0
    assert store["freeDeliveryAbove"] is None


def test_the_published_terms_produce_the_charged_total(app_client, seller_with_store):
    """The cart applies these rules client-side. If its arithmetic and the
    server's ever disagree, the buyer is quoted one number and charged another,
    so pin the server's answer against the same inputs the cart is given."""
    seller_with_store.put("/api/stores/me", json={"deliveryFee": 60, "freeDeliveryAbove": 999})
    product = make_product(seller_with_store, price=400, paymentMethods=["cod"])
    terms = shop(app_client, seller_with_store)["store"]

    # Below the threshold: delivery is charged.
    placed = place_order(app_client, seller_with_store.store_slug,
                         [{"productId": product["product_id"], "quantity": 1}],
                         payment_method="cod").json()
    quoted = 400 + (terms["deliveryFee"] if 400 < terms["freeDeliveryAbove"] else 0)
    assert placed["amount"] == quoted == 460

    # At the threshold: free, and "above ₹999" includes ₹999 to a buyer.
    seller_with_store.put("/api/stores/me", json={"freeDeliveryAbove": 800})
    terms = shop(app_client, seller_with_store)["store"]
    placed = place_order(app_client, seller_with_store.store_slug,
                         [{"productId": product["product_id"], "quantity": 2}],
                         payment_method="cod").json()
    quoted = 800 + (terms["deliveryFee"] if 800 < terms["freeDeliveryAbove"] else 0)
    assert placed["amount"] == quoted == 800


def test_the_receipt_total_matches_what_was_quoted(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me", json={"deliveryFee": 60})
    product = make_product(seller_with_store, price=400, paymentMethods=["cod"])
    placed = place_order(app_client, seller_with_store.store_slug,
                         [{"productId": product["product_id"], "quantity": 1}],
                         payment_method="cod").json()

    stored = seller_with_store.get(f"/api/orders/{placed['orderId']}").json()
    assert stored["subtotal"] == 400.0
    assert stored["deliveryFee"] == 60.0
    assert stored["amount"] == 460.0
