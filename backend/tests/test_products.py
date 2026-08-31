import io

from conftest import make_product


def test_create_product_generates_slug(seller_with_store):
    p = make_product(seller_with_store, title="Blue Cotton Kurta")
    assert p["slug"] == "blue-cotton-kurta"
    assert p["paymentMethods"] == ["online"]


def test_slug_collisions_get_suffixes(seller_with_store):
    slugs = [make_product(seller_with_store, title="Same Name")["slug"] for _ in range(3)]
    assert slugs == ["same-name", "same-name-2", "same-name-3"]


def test_editing_price_keeps_slug_but_retitling_changes_it(seller_with_store):
    p = make_product(seller_with_store, title="Clay Mug")
    pid = p["product_id"]

    same = seller_with_store.put(f"/api/products/{pid}",
                                 json={"title": "Clay Mug", "price": 999, "active": True}).json()
    assert same["slug"] == "clay-mug" and same["price"] == 999

    renamed = seller_with_store.put(f"/api/products/{pid}",
                                    json={"title": "Stone Mug", "price": 999, "active": True}).json()
    assert renamed["slug"] == "stone-mug"


def test_variants_round_trip(seller_with_store):
    p = make_product(seller_with_store, title="Tee", optionGroups=[
        {"name": "Size", "options": [
            {"label": "S", "priceDelta": 0, "stock": 5},
            {"label": "L", "priceDelta": 50, "stock": None},
        ]}
    ])
    groups = p["optionGroups"]
    assert groups[0]["name"] == "Size"
    assert [o["label"] for o in groups[0]["options"]] == ["S", "L"]
    assert groups[0]["options"][1]["priceDelta"] == 50


def test_payment_methods_persist_and_never_empty(seller_with_store):
    both = make_product(seller_with_store, title="Both", paymentMethods=["cod", "online"])
    assert both["paymentMethods"] == ["online", "cod"]  # stable order

    empty = make_product(seller_with_store, title="Empty", paymentMethods=[])
    assert empty["paymentMethods"] == ["online"]

    junk = make_product(seller_with_store, title="Junk", paymentMethods=["bitcoin"])
    assert junk["paymentMethods"] == ["online"]


def test_image_upload_and_gallery(app_client, seller_with_store):
    png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    paths = []
    for n in range(2):
        r = seller_with_store.post("/api/uploads/image?kind=product",
                                   files={"file": (f"a{n}.png", io.BytesIO(png), "image/png")})
        assert r.status_code == 200, r.text
        paths.append(r.json()["path"])

    p = make_product(seller_with_store, title="Pictured", images=paths)
    assert p["images"] == paths
    assert p["image"] == paths[0], "cover should be the first image"

    reordered = seller_with_store.put(f"/api/products/{p['product_id']}", json={
        "title": "Pictured", "price": 250, "active": True, "images": [paths[1]],
    }).json()
    assert reordered["images"] == [paths[1]] and reordered["image"] == paths[1]


def test_upload_rejects_non_image_extension(seller_with_store):
    r = seller_with_store.post("/api/uploads/image?kind=product",
                               files={"file": ("evil.svg", io.BytesIO(b"<svg/>"), "image/svg+xml")})
    assert r.status_code == 400


def test_inactive_products_hidden_from_public_shop(app_client, seller_with_store):
    make_product(seller_with_store, title="Live", active=True)
    make_product(seller_with_store, title="Draft", active=False)
    titles = [p["title"] for p in
              app_client.get(f"/api/shop/{seller_with_store.store_slug}").json()["products"]]
    assert titles == ["Live"]


def test_public_product_detail_and_related(app_client, seller_with_store):
    make_product(seller_with_store, title="Alpha")
    make_product(seller_with_store, title="Beta")
    make_product(seller_with_store, title="Gamma")

    r = app_client.get(f"/api/shop/{seller_with_store.store_slug}/product/beta")
    assert r.status_code == 200
    body = r.json()
    assert body["product"]["title"] == "Beta"
    assert body["store"]["slug"] == seller_with_store.store_slug
    related = {p["title"] for p in body["related"]}
    assert "Beta" not in related and related == {"Alpha", "Gamma"}


def test_public_product_detail_404s(app_client, seller_with_store):
    assert app_client.get(
        f"/api/shop/{seller_with_store.store_slug}/product/missing").status_code == 404


def test_delete_product(seller_with_store):
    p = make_product(seller_with_store)
    assert seller_with_store.delete(f"/api/products/{p['product_id']}").status_code == 200
    assert seller_with_store.get("/api/products").json() == []


def test_cannot_touch_another_sellers_product(make_seller, seller_with_store):
    p = make_product(seller_with_store)
    intruder = make_seller()
    intruder.post("/api/stores", json={"name": "Other", "slug": "other-shop-x"})
    assert intruder.put(f"/api/products/{p['product_id']}",
                        json={"title": "Hijacked", "price": 1, "active": True}).status_code == 404
    assert intruder.delete(f"/api/products/{p['product_id']}").status_code == 404


def test_price_must_be_positive(seller_with_store):
    r = seller_with_store.post("/api/products", json={"title": "Free", "price": 0, "active": True})
    assert r.status_code == 422
