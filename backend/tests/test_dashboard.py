"""The dashboard summary endpoint — every number the redesigned console shows.

These assert the arithmetic against orders the tests actually place, so a
regression in the aggregation shows up as a wrong figure, not a blank panel.
"""
from tests.conftest import make_product, place_order, raw_execute


def _paid(app_client, seller, product, qty=1, method="online"):
    r = place_order(app_client, seller.store_slug,
                    [{"productId": product["product_id"], "quantity": qty, "optionSelections": {}}],
                    payment_method=method)
    assert r.status_code == 200, r.text
    oid = r.json()["orderId"]
    raw_execute("UPDATE orders SET status = 'paid' WHERE order_id = $1", oid)
    return oid


def test_summary_requires_a_store(make_seller):
    s = make_seller()
    assert s.get("/api/dashboard/summary").status_code == 400


def test_empty_shop_returns_zeroes_not_nulls(seller_with_store):
    b = seller_with_store.get("/api/dashboard/summary").json()
    assert b["metrics"]["grossThisMonth"] == 0
    assert b["queue"]["toShip"] == 0
    assert b["topProducts"] == []
    assert len(b["daily"]) == 30
    assert all(d["amount"] == 0 for d in b["daily"])


def test_action_queue_counts_real_work(app_client, seller_with_store):
    p = make_product(seller_with_store, title="Runner", price=500, stock=10)
    low = make_product(seller_with_store, title="Almost gone", price=200, stock=2)
    make_product(seller_with_store, title="Sold out", price=200, stock=0)

    _paid(app_client, seller_with_store, p)
    _paid(app_client, seller_with_store, p)

    q = seller_with_store.get("/api/dashboard/summary").json()["queue"]
    assert q["toShip"] == 2
    assert q["toShipValue"] == 1000
    assert q["lowStock"] == 1 and q["outOfStock"] == 1
    assert "Almost gone" in q["lowStockTitles"]
    assert low["stock"] == 2


def test_awaiting_otp_counts_shipped_orders(app_client, seller_with_store):
    p = make_product(seller_with_store, price=500, stock=10)
    oid = _paid(app_client, seller_with_store, p)
    seller_with_store.post(f"/api/orders/{oid}/ship")

    q = seller_with_store.get("/api/dashboard/summary").json()["queue"]
    assert q["awaitingOtp"] == 1 and q["toShip"] == 0


def test_revenue_and_commission_arithmetic(app_client, seller_with_store):
    p = make_product(seller_with_store, price=1000, stock=50)
    for _ in range(3):
        _paid(app_client, seller_with_store, p)

    b = seller_with_store.get("/api/dashboard/summary").json()
    m = b["metrics"]
    assert m["grossThisMonth"] == 3000
    assert m["commissionThisMonth"] + m["netThisMonth"] == m["grossThisMonth"]
    assert m["netThisMonth"] == 3000 * (1 - m["commissionRate"])
    assert m["aov"] == 1000


def test_placed_but_unpaid_orders_are_not_revenue(app_client, seller_with_store):
    p = make_product(seller_with_store, price=1000, stock=50)
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}])
    b = seller_with_store.get("/api/dashboard/summary").json()
    assert b["metrics"]["grossThisMonth"] == 0
    assert b["metrics"]["totalOrders"] == 1


def test_cash_orders_are_tracked_apart_from_bank_money(app_client, seller_with_store):
    p = make_product(seller_with_store, price=800, stock=20, paymentMethods=["online", "cod"])
    oid = _paid(app_client, seller_with_store, p, method="cod")
    raw_execute("UPDATE orders SET status = 'completed' WHERE order_id = $1", oid)
    _paid(app_client, seller_with_store, p)  # online, still held

    money = seller_with_store.get("/api/dashboard/summary").json()["money"]
    assert money["cashCollected"] == 800
    assert money["held"] == 800          # only the online one
    assert money["cashCommissionOwed"] > 0


def test_top_products_rank_by_revenue(app_client, seller_with_store):
    cheap = make_product(seller_with_store, title="Mat", price=100, stock=99)
    dear = make_product(seller_with_store, title="Throw", price=2000, stock=99)
    _paid(app_client, seller_with_store, cheap, qty=5)
    _paid(app_client, seller_with_store, dear, qty=1)

    top = seller_with_store.get("/api/dashboard/summary").json()["topProducts"]
    assert [t["title"] for t in top] == ["Throw", "Mat"]
    assert top[0]["revenue"] == 2000 and top[1]["units"] == 5


def test_daily_series_is_zero_filled_and_dated(app_client, seller_with_store):
    p = make_product(seller_with_store, price=700, stock=10)
    _paid(app_client, seller_with_store, p)

    daily = seller_with_store.get("/api/dashboard/summary").json()["daily"]
    assert len(daily) == 30
    assert daily[-1]["amount"] == 700 and daily[-1]["orders"] == 1
    assert daily[0]["amount"] == 0
    assert daily[0]["date"] < daily[-1]["date"]


def test_health_checklist_reflects_the_real_shop(seller_with_store):
    h = seller_with_store.get("/api/dashboard/summary").json()["health"]
    assert h["hasBio"] is True          # the fixture writes one
    assert h["hasProducts"] is False
    assert h["hasGstin"] is False

    make_product(seller_with_store, paymentMethods=["online", "cod"])
    h = seller_with_store.get("/api/dashboard/summary").json()["health"]
    assert h["hasProducts"] is True and h["codEnabled"] is True


def test_repeat_buyers_counted_by_email(app_client, seller_with_store):
    p = make_product(seller_with_store, price=100, stock=99)
    for _ in range(2):
        _paid(app_client, seller_with_store, p)          # same default buyer
    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}],
                    buyer={"email": "someone.else@example.com"})
    # Must be paid to count: an abandoned order is not a buyer.
    raw_execute("UPDATE orders SET status = 'paid' WHERE order_id = $1", r.json()["orderId"])

    m = seller_with_store.get("/api/dashboard/summary").json()["metrics"]
    assert m["repeatBuyers"] == 1
    assert m["uniqueBuyers"] == 2


# --- bulk ship --------------------------------------------------------------
def test_bulk_ship_dispatches_many_and_reports_failures(app_client, seller_with_store):
    p = make_product(seller_with_store, price=500, stock=50)
    a, b = _paid(app_client, seller_with_store, p), _paid(app_client, seller_with_store, p)

    r = seller_with_store.post("/api/orders/bulk-ship",
                               json={"orderIds": [a, b, "order_does_not_exist"]})
    assert r.status_code == 200
    body = r.json()
    assert set(body["shipped"]) == {a, b}
    assert len(body["failed"]) == 1

    q = seller_with_store.get("/api/dashboard/summary").json()["queue"]
    assert q["toShip"] == 0 and q["awaitingOtp"] == 2


def test_bulk_ship_cannot_touch_another_sellers_orders(app_client, seller_with_store, make_seller):
    p = make_product(seller_with_store, price=500, stock=10)
    oid = _paid(app_client, seller_with_store, p)

    intruder = make_seller()
    intruder.post("/api/stores", json={"name": "Other", "slug": "other-shop-xyz"})
    r = intruder.post("/api/orders/bulk-ship", json={"orderIds": [oid]})
    assert r.json()["shipped"] == []
    assert len(r.json()["failed"]) == 1


# --- settings round-trip ----------------------------------------------------
def test_shop_settings_round_trip(seller_with_store):
    r = seller_with_store.put("/api/stores/me", json={
        "deliveryFee": 60, "freeDeliveryAbove": 1500, "dispatchDays": 2,
        "gstin": "32aabcu9603r1zm", "hsnCode": "5702",
        "notifyNewOrder": True, "notifyDailySummary": True, "notifyWeeklyDigest": False,
    })
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["deliveryFee"] == 60
    assert s["freeDeliveryAbove"] == 1500
    assert s["dispatchDays"] == 2
    assert s["gstin"] == "32AABCU9603R1ZM"      # normalised to upper case
    assert s["notifyDailySummary"] is True and s["notifyWeeklyDigest"] is False

    again = seller_with_store.get("/api/stores/me").json()
    assert again["gstin"] == "32AABCU9603R1ZM" and again["hsnCode"] == "5702"


def test_settings_defaults_are_sane_for_a_new_shop(seller_with_store):
    s = seller_with_store.get("/api/stores/me").json()
    assert s["deliveryFee"] == 0 and s["freeDeliveryAbove"] is None
    assert s["dispatchDays"] == 2 and s["gstin"] == ""
    assert s["notifyNewOrder"] is True


def test_customer_list_aggregates_spend_per_buyer(app_client, seller_with_store):
    p = make_product(seller_with_store, price=500, stock=99)
    for _ in range(3):
        _paid(app_client, seller_with_store, p)
    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}],
                    buyer={"name": "Solo Buyer", "email": "solo@example.com"})
    raw_execute("UPDATE orders SET status = 'paid' WHERE order_id = $1", r.json()["orderId"])

    customers = seller_with_store.get("/api/dashboard/summary").json()["customers"]
    top = customers[0]
    assert top["orders"] == 3 and top["spend"] == 1500
    assert {c["email"] for c in customers} == {"bob@example.com", "solo@example.com"}
    assert [c["spend"] for c in customers] == sorted([c["spend"] for c in customers], reverse=True)
