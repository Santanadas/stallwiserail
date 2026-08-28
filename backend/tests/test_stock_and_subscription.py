"""New feature tests: stock control and live Marketo Pro subscription create/verify."""
import uuid, requests


def _find_product(shop, title_contains):
    for p in shop["products"]:
        if title_contains.lower() in p["title"].lower():
            return p
    return None


# --- Stock display ---
def test_shop_returns_stock_fields(base_url):
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    assert shop["products"], "demo-store must have seeded products"
    # at least one product should expose stock (simple) or option stock
    any_stock = False
    for p in shop["products"]:
        if p.get("stock") is not None and not p.get("optionGroups"):
            any_stock = True
        for g in p.get("optionGroups") or []:
            for o in g["options"]:
                if o.get("stock") is not None:
                    any_stock = True
    assert any_stock, "expected at least one stock field in shop payload"


# --- Stock decrement on order ---
def test_stock_decrements_after_order(owner_session, base_url):
    # ensure mock payment
    owner_session.delete(f"{base_url}/api/seller/razorpay")
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    honey = _find_product(shop, "honey")
    if not honey or honey.get("stock") is None or (honey.get("optionGroups") or []):
        # create a fresh simple stocked product
        p = owner_session.post(f"{base_url}/api/products",
                               json={"title": f"TEST_Stock_{uuid.uuid4().hex[:6]}",
                                     "price": 100, "stock": 10, "optionGroups": [], "active": True})
        assert p.status_code in (200, 201), p.text
        shop = requests.get(f"{base_url}/api/shop/demo-store").json()
        honey = _find_product(shop, "TEST_Stock_")
    before = honey["stock"]
    guest = requests.Session(); guest.headers.update({"Content-Type": "application/json"})
    qty = 2
    r = guest.post(f"{base_url}/api/orders", json={
        "storeSlug": "demo-store",
        "buyerName": "Stock Buyer",
        "buyerEmail": "buyer@marketo-demo.com",
        "items": [{"productId": honey["product_id"], "title": honey["title"],
                   "quantity": qty, "optionSelections": {}}],
    })
    assert r.status_code in (200, 201), r.text
    shop2 = requests.get(f"{base_url}/api/shop/demo-store").json()
    honey2 = next(p for p in shop2["products"] if p["product_id"] == honey["product_id"])
    assert honey2["stock"] == before - qty, f"stock did not decrement: before={before} after={honey2['stock']}"


# --- Sell-out blocking (409) ---
def test_sellout_returns_409(owner_session, base_url):
    owner_session.delete(f"{base_url}/api/seller/razorpay")
    # create tiny-stock product
    title = f"TEST_Tiny_{uuid.uuid4().hex[:6]}"
    p = owner_session.post(f"{base_url}/api/products",
                           json={"title": title, "price": 50, "stock": 1,
                                 "optionGroups": [], "active": True})
    assert p.status_code in (200, 201), p.text
    pid = p.json().get("product_id") or p.json().get("id")
    if not pid:
        shop = requests.get(f"{base_url}/api/shop/demo-store").json()
        pid = _find_product(shop, title)["product_id"]
    guest = requests.Session(); guest.headers.update({"Content-Type": "application/json"})
    r = guest.post(f"{base_url}/api/orders", json={
        "storeSlug": "demo-store", "buyerName": "Buyer", "buyerEmail": "buyer@marketo-demo.com",
        "items": [{"productId": pid, "title": title, "quantity": 5, "optionSelections": {}}],
    })
    assert r.status_code == 409, f"expected 409 for oversell, got {r.status_code}: {r.text}"
    assert "out of stock" in r.text.lower()


# --- Option-level sell-out ---
def test_option_sellout_returns_409(owner_session, base_url):
    owner_session.delete(f"{base_url}/api/seller/razorpay")
    title = f"TEST_Opt_{uuid.uuid4().hex[:6]}"
    p = owner_session.post(f"{base_url}/api/products", json={
        "title": title, "price": 100, "stock": None, "active": True,
        "optionGroups": [{"name": "Size",
                          "options": [{"label": "S", "priceDelta": 0, "stock": 0},
                                      {"label": "M", "priceDelta": 0, "stock": 2}]}],
    })
    assert p.status_code in (200, 201), p.text
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    prod = _find_product(shop, title)
    guest = requests.Session(); guest.headers.update({"Content-Type": "application/json"})
    # order S which is 0
    r = guest.post(f"{base_url}/api/orders", json={
        "storeSlug": "demo-store", "buyerName": "B", "buyerEmail": "buyer@marketo-demo.com",
        "items": [{"productId": prod["product_id"], "title": title, "quantity": 1,
                   "optionSelections": {"Size": "S"}}],
    })
    assert r.status_code == 409
    # oversell M (2 in stock, order 3)
    r2 = guest.post(f"{base_url}/api/orders", json={
        "storeSlug": "demo-store", "buyerName": "B", "buyerEmail": "buyer@marketo-demo.com",
        "items": [{"productId": prod["product_id"], "title": title, "quantity": 3,
                   "optionSelections": {"Size": "M"}}],
    })
    assert r2.status_code == 409


# --- Subscription endpoints ---
def test_subscription_get_returns_billing_configured(owner_session, base_url):
    r = owner_session.get(f"{base_url}/api/subscription")
    assert r.status_code == 200
    j = r.json()
    assert j["premiumTier"] and j["plans"]["monthly"] and j["plans"]["yearly"]
    assert j.get("billingConfigured") is True, f"billingConfigured must be true for live buttons: {j}"


def test_subscription_create_returns_order(owner_session, base_url):
    r = owner_session.post(f"{base_url}/api/subscription/create", json={"interval": "monthly"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["mode"] in ("subscription", "onetime")
    if j["mode"] == "onetime":
        assert j.get("orderId", "").startswith("order_")
        assert j["amount"] == 199
    assert j.get("keyId")


def test_subscription_verify_rejects_bad_signature(owner_session, base_url):
    # first create so proOrderId is set
    c = owner_session.post(f"{base_url}/api/subscription/create", json={"interval": "monthly"}).json()
    if c.get("mode") != "onetime":
        return  # subscription mode uses different flow
    r = owner_session.post(f"{base_url}/api/subscription/verify-payment", json={
        "razorpay_order_id": c["orderId"],
        "razorpay_payment_id": "pay_TESTFAKE",
        "razorpay_signature": "deadbeef" * 8,
    })
    assert r.status_code == 400


def test_subscription_simulate_toggles_ads(owner_session, base_url):
    owner_session.post(f"{base_url}/api/subscription/simulate", json={"status": "active"})
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    assert shop["showAds"] is False
    owner_session.post(f"{base_url}/api/subscription/simulate", json={"status": "inactive"})
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    assert shop["showAds"] is True
