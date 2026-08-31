from conftest import make_product, place_order


def _item(p, qty=1, options=None):
    return {"productId": p["product_id"], "quantity": qty, "optionSelections": options or {}}


# --------------------------------------------------------------- online flow
def test_online_checkout_creates_razorpay_order(app_client, seller_with_store):
    p = make_product(seller_with_store, price=500)
    r = place_order(app_client, seller_with_store.store_slug, [_item(p)])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["amount"] == 500
    assert body["paymentMethod"] == "online"
    assert body["razorpayOrderId"].startswith("order_")
    assert body["razorpayKeyId"] == "rzp_test_fake"


def test_price_is_computed_server_side_from_variants(app_client, seller_with_store):
    p = make_product(seller_with_store, price=100, optionGroups=[
        {"name": "Size", "options": [{"label": "S", "priceDelta": 0},
                                     {"label": "L", "priceDelta": 40}]}
    ])
    r = place_order(app_client, seller_with_store.store_slug,
                    [_item(p, qty=2, options={"Size": "L"})])
    assert r.json()["amount"] == 280  # (100 + 40) * 2


def test_missing_variant_selection_rejected(app_client, seller_with_store):
    p = make_product(seller_with_store, optionGroups=[
        {"name": "Size", "options": [{"label": "S", "priceDelta": 0}]}
    ])
    r = place_order(app_client, seller_with_store.store_slug, [_item(p)])
    assert r.status_code == 400 and "Size" in r.json()["detail"]


def test_unknown_product_rejected(app_client, seller_with_store):
    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": "prod_nope", "quantity": 1, "optionSelections": {}}])
    assert r.status_code == 400


def test_cannot_buy_another_stores_product(app_client, make_seller, seller_with_store):
    other = make_seller()
    other.post("/api/stores", json={"name": "Other", "slug": "other-store-z"})
    theirs = make_product(other, title="Theirs")
    r = place_order(app_client, seller_with_store.store_slug, [_item(theirs)])
    assert r.status_code == 400


# ------------------------------------------------------------------- stock
def test_oversell_is_rejected_and_stock_decrements(app_client, seller_with_store):
    p = make_product(seller_with_store, stock=5)

    too_many = place_order(app_client, seller_with_store.store_slug, [_item(p, qty=9)])
    assert too_many.status_code == 409

    ok = place_order(app_client, seller_with_store.store_slug, [_item(p, qty=2)])
    assert ok.status_code == 200

    remaining = seller_with_store.get("/api/products").json()[0]["stock"]
    assert remaining == 3


def test_unlimited_stock_never_blocks(app_client, seller_with_store):
    p = make_product(seller_with_store, stock=None)
    assert place_order(app_client, seller_with_store.store_slug,
                       [_item(p, qty=500)]).status_code == 200


# --------------------------------------------------------- payment methods
def test_cod_allowed_when_every_item_accepts_it(app_client, seller_with_store):
    p = make_product(seller_with_store, paymentMethods=["online", "cod"])
    r = place_order(app_client, seller_with_store.store_slug, [_item(p)], payment_method="cod")
    assert r.status_code == 200
    body = r.json()
    assert body["paymentMethod"] == "cod"
    assert body["razorpayOrderId"] is None, "COD must not touch the gateway"


def test_cod_rejected_for_online_only_product(app_client, seller_with_store):
    p = make_product(seller_with_store, paymentMethods=["online"])
    r = place_order(app_client, seller_with_store.store_slug, [_item(p)], payment_method="cod")
    assert r.status_code == 400
    assert "cash on delivery" in r.json()["detail"].lower()


def test_cod_rejected_for_mixed_cart(app_client, seller_with_store):
    both = make_product(seller_with_store, title="Both", paymentMethods=["online", "cod"])
    online = make_product(seller_with_store, title="OnlineOnly", paymentMethods=["online"])
    r = place_order(app_client, seller_with_store.store_slug,
                    [_item(both), _item(online)], payment_method="cod")
    assert r.status_code == 400


def test_unknown_payment_method_rejected(app_client, seller_with_store):
    p = make_product(seller_with_store)
    r = place_order(app_client, seller_with_store.store_slug, [_item(p)], payment_method="crypto")
    assert r.status_code == 400


# ---------------------------------------------------------------- lifecycle
def _paid_cod_order(app_client, seller):
    p = make_product(seller, price=300, paymentMethods=["online", "cod"])
    r = place_order(app_client, seller.store_slug, [_item(p)], payment_method="cod")
    return r.json()["orderId"]


def test_cod_lifecycle_ship_confirm_and_window(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me", json={"acceptanceWindowMinutes": 60})
    oid = _paid_cod_order(app_client, seller_with_store)

    detail = seller_with_store.get(f"/api/orders/{oid}").json()
    assert detail["status"] == "placed" and detail["paidAt"] is None

    # COD ships straight from placed — there is no payment leg.
    assert seller_with_store.post(f"/api/orders/{oid}/ship").status_code == 200

    otp = app_client.get(f"/api/order/{oid}", params={"email": "bob@example.com"}).json()["otp"]
    done = seller_with_store.post(f"/api/orders/{oid}/confirm-delivery", json={"otp": otp})
    assert done.status_code == 200

    final = seller_with_store.get(f"/api/orders/{oid}").json()
    assert final["status"] == "delivered"
    assert final["windowExpiresAt"], "acceptance window must be stamped"
    assert final["paidAt"], "cash is collected at handover, so paidAt is set"


def test_online_order_cannot_ship_before_payment(app_client, seller_with_store):
    p = make_product(seller_with_store)
    oid = place_order(app_client, seller_with_store.store_slug, [_item(p)]).json()["orderId"]
    r = seller_with_store.post(f"/api/orders/{oid}/ship")
    assert r.status_code == 400 and "paid" in r.json()["detail"].lower()


def test_wrong_otp_locks_after_five_attempts(app_client, seller_with_store):
    oid = _paid_cod_order(app_client, seller_with_store)
    seller_with_store.post(f"/api/orders/{oid}/ship")
    codes = ["000000"] * 5
    statuses = [seller_with_store.post(f"/api/orders/{oid}/confirm-delivery",
                                       json={"otp": c}).status_code for c in codes]
    assert statuses[-1] == 423, statuses
    assert seller_with_store.get(f"/api/orders/{oid}").json()["otpLocked"] is True


def test_dispute_requires_matching_email_and_delivered_state(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me", json={"acceptanceWindowMinutes": 60})
    oid = _paid_cod_order(app_client, seller_with_store)

    early = app_client.post(f"/api/order/{oid}/dispute",
                            json={"email": "bob@example.com", "reason": "too soon"})
    assert early.status_code == 400

    seller_with_store.post(f"/api/orders/{oid}/ship")
    otp = app_client.get(f"/api/order/{oid}", params={"email": "bob@example.com"}).json()["otp"]
    seller_with_store.post(f"/api/orders/{oid}/confirm-delivery", json={"otp": otp})

    wrong = app_client.post(f"/api/order/{oid}/dispute",
                            json={"email": "someone@else.com", "reason": "not mine"})
    assert wrong.status_code == 403

    ok = app_client.post(f"/api/order/{oid}/dispute",
                         json={"email": "bob@example.com", "reason": "arrived broken"})
    assert ok.status_code == 200
    final = seller_with_store.get(f"/api/orders/{oid}").json()
    assert final["status"] == "disputed"
    assert final["disputeRaised"] is True
    assert final["disputeReason"] == "arrived broken"


def test_order_auto_completes_once_window_passes(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me", json={"acceptanceWindowMinutes": 1})
    oid = _paid_cod_order(app_client, seller_with_store)
    seller_with_store.post(f"/api/orders/{oid}/ship")
    otp = app_client.get(f"/api/order/{oid}", params={"email": "bob@example.com"}).json()["otp"]
    seller_with_store.post(f"/api/orders/{oid}/confirm-delivery", json={"otp": otp})

    # Rewind the window rather than sleeping.
    import db
    from datetime import datetime, timedelta, timezone
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    conn = db._get_sqlite_conn()
    with conn:
        conn.execute("UPDATE orders SET window_expires_at = ? WHERE order_id = ?", (past, oid))
    assert seller_with_store.get(f"/api/orders/{oid}").json()["status"] == "completed"


# ------------------------------------------------------------------ privacy
def test_buyer_order_requires_matching_email(app_client, seller_with_store):
    oid = _paid_cod_order(app_client, seller_with_store)
    assert app_client.get(f"/api/order/{oid}").status_code == 404
    assert app_client.get(f"/api/order/{oid}",
                          params={"email": "wrong@example.com"}).status_code == 404
    assert app_client.get(f"/api/order/{oid}",
                          params={"email": "bob@example.com"}).status_code == 200


def test_seller_cannot_read_another_sellers_order(app_client, make_seller, seller_with_store):
    oid = _paid_cod_order(app_client, seller_with_store)
    other = make_seller()
    other.post("/api/stores", json={"name": "Other", "slug": "other-store-y"})
    assert other.get(f"/api/orders/{oid}").status_code == 404


def test_order_list_filters_by_status(app_client, seller_with_store):
    _paid_cod_order(app_client, seller_with_store)
    assert seller_with_store.get("/api/orders?status=placed").json()["total"] == 1
    assert seller_with_store.get("/api/orders?status=completed").json()["total"] == 0
