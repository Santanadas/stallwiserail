import uuid

from conftest import make_product


def test_create_store_and_fetch_it(make_seller):
    s = make_seller()
    slug = f"shop-{uuid.uuid4().hex[:8]}"
    r = s.post("/api/stores", json={"name": "Clay Co", "slug": slug, "bio": "Pots."})
    assert r.status_code == 200
    assert r.json()["slug"] == slug

    mine = s.get("/api/stores/me").json()
    assert mine["name"] == "Clay Co"
    assert mine["routeConnected"] is False


def test_invalid_slugs_are_rejected(make_seller):
    for bad in ["Not Valid", "trailing-", "sym$bol", "under_score", "a"]:
        s = make_seller()
        r = s.post("/api/stores", json={"name": "X", "slug": bad})
        assert r.status_code in (400, 422), f"{bad!r} was accepted"


def test_uppercase_slug_is_normalised_not_rejected(make_seller):
    s = make_seller()
    r = s.post("/api/stores", json={"name": "X", "slug": "MixedCase"})
    assert r.status_code == 200
    assert r.json()["slug"] == "mixedcase"


def test_slug_is_unique_across_sellers(make_seller):
    slug = f"shop-{uuid.uuid4().hex[:8]}"
    a, b = make_seller(), make_seller()
    assert a.post("/api/stores", json={"name": "A", "slug": slug}).status_code == 200
    r = b.post("/api/stores", json={"name": "B", "slug": slug})
    assert r.status_code == 400 and "taken" in r.json()["detail"].lower()


def test_one_store_per_seller(seller_with_store):
    r = seller_with_store.post("/api/stores", json={"name": "Second", "slug": "second-shop"})
    assert r.status_code == 400


def test_update_store_fields(seller_with_store):
    r = seller_with_store.put("/api/stores/me",
                              json={"name": "Renamed", "bio": "New bio", "acceptanceWindowMinutes": 45})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Renamed" and body["acceptanceWindowMinutes"] == 45


def test_public_shop_endpoint(app_client, seller_with_store):
    make_product(seller_with_store, title="Bowl")
    r = app_client.get(f"/api/shop/{seller_with_store.store_slug}")
    assert r.status_code == 200
    body = r.json()
    assert body["store"]["slug"] == seller_with_store.store_slug
    assert [p["title"] for p in body["products"]] == ["Bowl"]
    # Free plan shows ads.
    assert body["showAds"] is True


def test_public_shop_404(app_client):
    assert app_client.get("/api/shop/nope-does-not-exist").status_code == 404


def test_shop_directory_excludes_empty_shops(app_client, make_seller):
    empty = make_seller()
    empty.post("/api/stores", json={"name": "Empty", "slug": "empty-shop"})
    stocked = make_seller()
    stocked.post("/api/stores", json={"name": "Stocked", "slug": "stocked-shop"})
    make_product(stocked, title="Thing")

    slugs = [s["slug"] for s in app_client.get("/api/shops").json()["shops"]]
    assert "stocked-shop" in slugs
    assert "empty-shop" not in slugs
