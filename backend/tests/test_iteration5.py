"""Iteration 5: uploads, files, seller Route (Partner), bio, orders pagination, public shop."""
import io, uuid, struct, zlib, requests

def _png_bytes():
    # minimal 1x1 red PNG
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# --- Uploads ---
def test_upload_product_image_and_serve(owner_session, base_url):
    files = {"file": ("t.png", _png_bytes(), "image/png")}
    # requests overrides content-type header automatically for multipart, but session has json header set
    s = owner_session
    # remove JSON content-type header for multipart
    s.headers.pop("Content-Type", None)
    r = s.post(f"{base_url}/api/uploads/image", params={"kind": "product"}, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "path" in body and "url" in body
    assert body["url"].startswith("/api/files/")

    # serve public
    g = requests.get(f"{base_url}{body['url']}")
    assert g.status_code == 200
    assert g.headers.get("content-type", "").startswith("image/")


def test_upload_avatar_sets_user(owner_session, base_url):
    s = owner_session
    s.headers.pop("Content-Type", None)
    files = {"file": ("a.png", _png_bytes(), "image/png")}
    r = s.post(f"{base_url}/api/uploads/image", params={"kind": "avatar"}, files=files)
    assert r.status_code == 200, r.text
    path = r.json()["path"]
    me = s.get(f"{base_url}/api/auth/me").json()
    assert me.get("avatar") == path


# --- Route onboarding ---
def test_route_onboard_mock_fallback(owner_session, base_url):
    owner_session.headers.update({"Content-Type": "application/json"})
    payload = {
        "legal_business_name": "Marketo Demo LLP",
        "contact_name": "Test Owner",
        "phone": "9999999999",
        "business_type": "individual",
        "beneficiary_name": "Test Owner",
        "account_number": "123456789012",
        "ifsc": "HDFC0001234",
    }
    r = owner_session.post(f"{base_url}/api/seller/route/onboard", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["connected"] is True
    assert body["mode"] in ("mock", "razorpay")  # mock expected on test key
    assert body.get("status")
    assert body.get("accountIdLast4") and len(body["accountIdLast4"]) == 4
    assert body.get("bankLast4") == "9012"

    # GET reflects
    r2 = owner_session.get(f"{base_url}/api/seller/route")
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2["connected"] is True
    assert j2["mode"] == body["mode"]

    # Store surfaces routeConnected/routeMode/routeStatus + bio
    st = owner_session.get(f"{base_url}/api/stores/me").json()
    assert st.get("routeConnected") is True
    assert st.get("routeMode") == body["mode"]
    assert st.get("routeStatus")
    assert "bio" in st


def test_route_disconnect(owner_session, base_url):
    r = owner_session.delete(f"{base_url}/api/seller/route")
    assert r.status_code == 200
    assert r.json().get("connected") is False
    r2 = owner_session.get(f"{base_url}/api/seller/route")
    assert r2.json().get("connected") is False


# --- Public shop ---
def test_public_shop_bio_and_seller(base_url):
    r = requests.get(f"{base_url}/api/shop/demo-store")
    assert r.status_code == 200
    j = r.json()
    assert j["store"].get("bio")
    assert j.get("seller", {}).get("name")
    assert "products" in j


# --- Orders pagination ---
def test_orders_pagination(owner_session, base_url):
    owner_session.headers.update({"Content-Type": "application/json"})
    r = owner_session.get(f"{base_url}/api/orders", params={"page": 1, "limit": 5})
    assert r.status_code == 200, r.text
    j = r.json()
    for k in ("orders", "total", "page", "pages", "limit"):
        assert k in j, f"missing key {k}"
    assert j["page"] == 1
    assert j["limit"] == 5
    assert isinstance(j["orders"], list)
    assert len(j["orders"]) <= 5

    # page 2 if available
    if j["pages"] >= 2:
        r2 = owner_session.get(f"{base_url}/api/orders", params={"page": 2, "limit": 5})
        assert r2.status_code == 200
        key = "order_id" if "order_id" in j["orders"][0] else "orderId"
        ids1 = {o[key] for o in j["orders"]}
        ids2 = {o[key] for o in r2.json()["orders"]}
        assert not (ids1 & ids2), "page 1 and page 2 overlap"

    # status filter still works
    rf = owner_session.get(f"{base_url}/api/orders", params={"page": 1, "limit": 5, "status": "placed"})
    assert rf.status_code == 200
    for o in rf.json()["orders"]:
        assert o["status"] == "placed"


# --- Register new seller (onboarding precondition) ---
def test_register_new_seller_has_no_store(api, base_url):
    email = f"TEST_onb_{uuid.uuid4().hex[:8]}@marketo-demo.com"
    r = api.post(f"{base_url}/api/auth/register", json={"name": "Onb", "email": email, "password": "Test@1234"})
    assert r.status_code in (200, 201), r.text
    # cookie session established; check store lookup returns "no store"
    r2 = api.get(f"{base_url}/api/stores/me")
    # backend may return 200 with null or 404
    assert r2.status_code in (200, 404)
    if r2.status_code == 200:
        j = r2.json()
        assert not j or not j.get("slug"), f"new seller unexpectedly has store: {j}"
