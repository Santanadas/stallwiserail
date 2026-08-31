"""SEO output and the security regressions we've already fixed once."""
import io

import pytest

import security
from conftest import make_product


# --------------------------------------------------------------------- SEO
def test_store_page_renders_its_own_meta(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me",
                          json={"name": "Studio Craft", "bio": "Handmade stoneware from Kolkata."})
    make_product(seller_with_store, title="Speckled Mug", price=499)

    html = app_client.get(f"/{seller_with_store.store_slug}").text
    assert "<title>Studio Craft — Shop Online | Stall Wise</title>" in html
    assert "Handmade stoneware from Kolkata." in html
    assert f'rel="canonical" href="https://stallwise.in/{seller_with_store.store_slug}"' in html
    assert '"@type":"Store"' in html
    assert "makesOffer" in html


def test_product_page_renders_product_schema(app_client, seller_with_store):
    seller_with_store.put("/api/stores/me", json={"name": "Studio Craft"})
    make_product(seller_with_store, title="Speckled Mug", price=499)

    html = app_client.get(f"/{seller_with_store.store_slug}/speckled-mug").text
    assert "<title>Speckled Mug — ₹499 | Studio Craft</title>" in html
    assert 'property="og:type" content="product"' in html
    assert '"@type":"Product"' in html
    assert '"@type":"BreadcrumbList"' in html
    assert '"priceCurrency":"INR"' in html


def test_seo_tags_are_never_duplicated(app_client, seller_with_store):
    make_product(seller_with_store, title="Thing")
    html = app_client.get(f"/{seller_with_store.store_slug}").text
    assert html.count("<title>") == 1
    assert html.count('rel="canonical"') == 1
    assert html.count('property="og:title"') == 1


def test_unknown_product_is_noindexed_not_soft_404(app_client, seller_with_store):
    html = app_client.get(f"/{seller_with_store.store_slug}/no-such-product").text
    assert 'name="robots" content="noindex, nofollow"' in html
    assert f'rel="canonical" href="https://stallwise.in/{seller_with_store.store_slug}"' in html


@pytest.mark.parametrize("route", ["dashboard", "login", "onboarding", "orders/abc", "order/abc"])
def test_private_routes_are_noindexed(app_client, route):
    assert 'content="noindex, nofollow"' in app_client.get(f"/{route}").text


@pytest.mark.parametrize("route,fragment", [
    ("about", "About Stall Wise"),
    ("sell-online", "How to Sell Online in India"),
    ("shops", "Browse Shops on Stall Wise"),
])
def test_static_pages_have_their_own_titles(app_client, route, fragment):
    assert fragment in app_client.get(f"/{route}").text


def test_robots_txt_blocks_private_areas(app_client):
    body = app_client.get("/robots.txt").text
    assert "Disallow: /dashboard" in body
    assert "Disallow: /api/" in body
    assert "Sitemap: https://stallwise.in/sitemap.xml" in body


def test_sitemap_lists_stores_and_products(app_client, seller_with_store):
    make_product(seller_with_store, title="Speckled Mug")
    xml = app_client.get("/sitemap.xml").text
    assert f"<loc>https://stallwise.in/{seller_with_store.store_slug}</loc>" in xml
    assert f"<loc>https://stallwise.in/{seller_with_store.store_slug}/speckled-mug</loc>" in xml
    assert "<loc>https://stallwise.in/shops</loc>" in xml


def test_no_broken_og_image_when_no_asset_exists(app_client, seller_with_store):
    html = app_client.get(f"/{seller_with_store.store_slug}").text
    if 'property="og:image"' not in html:
        assert 'name="twitter:card" content="summary"' in html


# ---------------------------------------------------------------- security
@pytest.mark.parametrize("path", [
    "../../../../etc/passwd",
    "marketo/uploads/../../../../etc/passwd",
    "..",
    "marketo/../../server.py",
])
def test_storage_resolver_rejects_traversal(path):
    """The guard lives here. HTTP clients normalise `..` out of a URL before it
    ever reaches the server, so asserting on the route alone proves nothing."""
    import storage
    with pytest.raises(ValueError):
        storage._resolve(path)


@pytest.mark.parametrize("path", [
    "..%2f..%2f..%2fetc%2fpasswd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "marketo%2Fuploads%2F..%2F..%2Fserver.py",
])
def test_file_route_never_leaks_files(app_client, path):
    """Encoded traversal survives client normalisation and must 404."""
    r = app_client.get(f"/api/files/{path}")
    assert r.status_code == 404
    assert b"root:" not in r.content
    assert b"FastAPI" not in r.content


def test_absolute_paths_are_neutralised_into_the_upload_dir(tmp_path, monkeypatch):
    """A leading slash is stripped rather than rejected, so /etc/passwd becomes
    a harmless relative key that simply does not exist."""
    import storage
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    assert storage._resolve("/etc/passwd").startswith(str(tmp_path.resolve()))
    with pytest.raises(FileNotFoundError):
        storage.get_object("/etc/passwd")


def test_storage_resolver_allows_normal_keys(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "UPLOAD_DIR", str(tmp_path))
    resolved = storage._resolve("marketo/uploads/user_1/a.png")
    assert resolved.startswith(str(tmp_path.resolve()))


def test_uploaded_file_is_served_with_nosniff(app_client, seller_with_store):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    stored = seller_with_store.post("/api/uploads/image?kind=product",
                                    files={"file": ("a.png", io.BytesIO(png), "image/png")}).json()
    r = app_client.get(f"/api/files/{stored['path']}")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-type"].startswith("image/png")


@pytest.mark.parametrize("path,ok", [
    ("marketo/uploads/user_1/a.png", True),
    ("/api/files/marketo/uploads/user_1/a.png", True),
    ("https://cdn.example.com/a.jpg", True),
    ("../etc/passwd", False),
    ("marketo/uploads/../../x", False),
    ("javascript:alert(1)", False),
])
def test_is_safe_image_path(path, ok):
    assert security.is_safe_image_path(path) is ok


def test_delivery_otp_is_encrypted_at_rest(app_client, seller_with_store):
    import db
    from conftest import place_order
    p = make_product(seller_with_store, paymentMethods=["online", "cod"])
    oid = place_order(app_client, seller_with_store.store_slug,
                      [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}],
                      payment_method="cod").json()["orderId"]
    seller_with_store.post(f"/api/orders/{oid}/ship")
    otp = app_client.get(f"/api/order/{oid}", params={"email": "bob@example.com"}).json()["otp"]

    from tests.conftest import raw_fetch_one
    row = raw_fetch_one("SELECT otp_enc, otp_code_hash FROM orders WHERE order_id = $1", oid)
    assert row, "order row missing"
    assert otp not in (row["otp_enc"] or ""), "OTP must not be stored in plaintext"
    assert otp not in (row["otp_code_hash"] or ""), "the stored hash must not be the plaintext OTP"


def test_protected_endpoints_require_auth(app_client):
    for path in ["/api/products", "/api/orders", "/api/stores/me", "/api/seller/route"]:
        assert app_client.get(path).status_code == 401, path
