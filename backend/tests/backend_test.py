"""Marketo backend smoke tests — auth, stores, products, orders lifecycle, subscription."""
import time, uuid, requests

# --- Auth ---
def test_login_owner(owner_session, base_url):
    r = owner_session.get(f"{base_url}/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "bongsharnipan123@gmail.com"

def test_login_bad_creds(api, base_url):
    r = api.post(f"{base_url}/api/auth/login", json={"email": "nope@marketo-demo.com", "password": "wrong"})
    assert r.status_code in (400, 401)

def test_forgot_password_generic(api, base_url):
    r = api.post(f"{base_url}/api/auth/forgot-password", json={"email": "unknown@marketo-demo.com"})
    assert r.status_code == 200
    assert "message" in r.json()

def test_register_new_seller(api, base_url):
    email = f"TEST_seller_{uuid.uuid4().hex[:8]}@marketo-demo.com"
    r = api.post(f"{base_url}/api/auth/register", json={"name": "T", "email": email, "password": "Test@1234"})
    assert r.status_code in (200, 201), r.text
    # new seller has no store
    r2 = api.get(f"{base_url}/api/stores/me")
    assert r2.status_code in (200, 404)

# --- Store & Razorpay ---
def test_owner_store_exists(owner_session, base_url):
    r = owner_session.get(f"{base_url}/api/stores/me")
    assert r.status_code == 200
    assert r.json()["slug"] == "demo-store"

def test_razorpay_connect_and_hide_secret(owner_session, base_url):
    payload = {"key_id": "rzp_test_ABCDEFGH1234", "key_secret": "supersecretplaintext"}
    r = owner_session.post(f"{base_url}/api/seller/razorpay", json=payload)
    assert r.status_code in (200, 201)
    r2 = owner_session.get(f"{base_url}/api/seller/razorpay")
    assert r2.status_code == 200
    body = r2.json()
    assert body.get("connected") is True
    # secret must not be exposed
    assert "supersecretplaintext" not in r2.text
    assert "key_secret" not in body or not body.get("key_secret")

# --- Products & Shop ---
def test_shop_public_and_products(owner_session, base_url):
    r = owner_session.get(f"{base_url}/api/shop/demo-store")
    assert r.status_code == 200
    j = r.json()
    assert "products" in j and "store" in j and "showAds" in j

# --- Order lifecycle with mock payment ---
def test_order_lifecycle_mock(owner_session, base_url):
    # Get first product
    shop = owner_session.get(f"{base_url}/api/shop/demo-store").json()
    if not shop["products"]:
        # create one
        p = owner_session.post(f"{base_url}/api/products", json={"title": "TEST_P", "price": 100, "stock": 10, "optionGroups": [], "active": True})
        assert p.status_code in (200, 201), p.text
        shop = owner_session.get(f"{base_url}/api/shop/demo-store").json()
    prod = shop["products"][0]
    sel = {}
    for g in prod.get("optionGroups") or []:
        sel[g["name"]] = g["options"][0]["label"]

    # Disconnect razorpay to force mockPayment
    owner_session.delete(f"{base_url}/api/seller/razorpay")

    # Place order (guest)
    guest = requests.Session()
    guest.headers.update({"Content-Type": "application/json"})
    r = guest.post(f"{base_url}/api/orders", json={
        "storeSlug": "demo-store",
        "buyerName": "Test Buyer",
        "buyerEmail": "buyer@marketo-demo.com",
        "items": [{"productId": prod["product_id"], "title": prod["title"], "quantity": 1, "optionSelections": sel}],
        "acceptanceWindowMinutes": 1,
    })
    assert r.status_code in (200, 201), r.text
    order_id = r.json()["orderId"]

    # Buyer view
    b = guest.get(f"{base_url}/api/buyer/orders/{order_id}", params={"email": "buyer@marketo-demo.com"})
    assert b.status_code == 200
    assert b.json()["status"] == "placed"
    assert b.json().get("mockPayment") is True

    # Simulate payment
    p = guest.post(f"{base_url}/api/orders/{order_id}/simulate-payment")
    assert p.status_code == 200, p.text

    b = guest.get(f"{base_url}/api/buyer/orders/{order_id}", params={"email": "buyer@marketo-demo.com"}).json()
    assert b["status"] == "paid"
    # OTP should NOT be exposed yet (issued on ship)
    assert not b.get("otp")

    # Seller: ship (issues OTP)
    s = owner_session.post(f"{base_url}/api/orders/{order_id}/ship")
    assert s.status_code == 200, s.text

    # Buyer now sees OTP
    b = guest.get(f"{base_url}/api/buyer/orders/{order_id}", params={"email": "buyer@marketo-demo.com"}).json()
    otp = b.get("otp")
    assert otp and len(str(otp)) >= 4, f"OTP not exposed to buyer after ship: {b}"

    # Seller sees no OTP
    sv = owner_session.get(f"{base_url}/api/orders/{order_id}").json()
    assert "otp" not in sv or not sv.get("otp")
    assert "otpCodeHash" not in sv or not sv.get("otpCodeHash")

    # Out for delivery
    o = owner_session.post(f"{base_url}/api/orders/{order_id}/out-for-delivery")
    assert o.status_code == 200

    # Wrong OTP
    bad = owner_session.post(f"{base_url}/api/orders/{order_id}/confirm-delivery", json={"otp": "000000"})
    assert bad.status_code in (400, 401, 422)

    # Correct OTP
    good = owner_session.post(f"{base_url}/api/orders/{order_id}/confirm-delivery", json={"otp": str(otp)})
    assert good.status_code == 200, good.text
    sv = owner_session.get(f"{base_url}/api/orders/{order_id}").json()
    assert sv["status"] == "delivered_confirmed"
    assert sv.get("windowExpiresAt")

    # Buyer disputes within window
    d = guest.post(f"{base_url}/api/buyer/orders/{order_id}/dispute", params={"email": "buyer@marketo-demo.com"}, json={"reason": "damaged"})
    assert d.status_code == 200, d.text
    sv = owner_session.get(f"{base_url}/api/orders/{order_id}").json()
    assert sv["status"] == "disputed"

# --- Subscription toggle ---
def test_subscription_toggle_hides_ads(owner_session, base_url):
    # activate
    r = owner_session.post(f"{base_url}/api/subscription/simulate", json={"status": "active"})
    assert r.status_code == 200
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    assert shop["showAds"] is False
    # deactivate
    owner_session.post(f"{base_url}/api/subscription/simulate", json={"status": "inactive"})
    shop = requests.get(f"{base_url}/api/shop/demo-store").json()
    assert shop["showAds"] is True
