"""Catalogue details beyond title and price.

MRP, SKU, category, brand, condition, highlights, specifications, and the
country-of-origin and manufacturer lines Indian e-commerce rules ask for. All
optional — the rules worth pinning are the ones with consequences: MRP is a
ceiling, the SKU is the seller's alone, and seller text can't break out of the
structured data on the server-rendered page.
"""
import json

import seo
from conftest import make_product, place_order, raw_execute, raw_fetch_one

DETAILS = {
    "mrp": 999,
    "sku": "KRT-BLU-M",
    "category": "fashion",
    "brand": "Neel",
    "condition": "refurbished",
    "highlights": ["Hand block printed", "", "  Pure cotton  "],
    "specs": [
        {"name": "Fabric", "value": "Cotton"},
        {"name": "fabric", "value": "Silk"},
        {"name": "Fit", "value": ""},
        {"name": "", "value": "orphan"},
    ],
    "countryOfOrigin": "India",
    "manufacturer": "Neel Textiles, Jaipur 302001",
}


def _by_id(seller, pid):
    return next(p for p in seller.get("/api/products").json() if p["product_id"] == pid)


def test_details_round_trip_and_are_cleaned(seller_with_store):
    p = make_product(seller_with_store, title="Blue Kurta", price=599, **DETAILS)
    assert p["mrp"] == 999
    assert p["sku"] == "KRT-BLU-M"
    assert (p["category"], p["brand"], p["condition"]) == ("fashion", "Neel", "refurbished")
    assert p["highlights"] == ["Hand block printed", "Pure cotton"]
    # Blank rows are dropped, and a second "fabric" can't contradict the first.
    assert p["specs"] == [{"name": "Fabric", "value": "Cotton"}]
    assert p["countryOfOrigin"] == "India"
    assert p["manufacturer"] == "Neel Textiles, Jaipur 302001"
    assert _by_id(seller_with_store, p["product_id"]) == p

    edited = seller_with_store.put(f"/api/products/{p['product_id']}", json={
        "title": "Blue Kurta", "price": 599, "active": True, **DETAILS,
        "specs": [{"name": "Fit", "value": "Relaxed"}], "mrp": None,
    })
    assert edited.status_code == 200, edited.text
    assert edited.json()["specs"] == [{"name": "Fit", "value": "Relaxed"}]
    assert edited.json()["mrp"] is None


def test_buyers_see_the_details_but_never_the_sku(app_client, seller_with_store):
    p = make_product(seller_with_store, title="Clay Lamp", price=450, **DETAILS)
    slug = seller_with_store.store_slug
    listed = next(x for x in app_client.get(f"/api/shop/{slug}").json()["products"]
                  if x["product_id"] == p["product_id"])
    detail = app_client.get(f"/api/shop/{slug}/product/{p['slug']}").json()["product"]
    for view in (listed, detail):
        assert "sku" not in view
        assert view["mrp"] == 999
        assert view["specs"] == [{"name": "Fabric", "value": "Cotton"}]


def test_mrp_below_the_price_is_refused(seller_with_store):
    r = seller_with_store.post("/api/products",
                               json={"title": "Too dear", "price": 599, "mrp": 500, "active": True})
    assert r.status_code == 400 and "MRP" in r.json()["detail"]

    p = make_product(seller_with_store, title="Fine", price=599, mrp=699)
    r = seller_with_store.put(f"/api/products/{p['product_id']}",
                              json={"title": "Fine", "price": 799, "mrp": 699, "active": True})
    assert r.status_code == 400
    assert _by_id(seller_with_store, p["product_id"])["price"] == 599


def test_mrp_equal_blank_or_zero_is_accepted(seller_with_store):
    assert make_product(seller_with_store, title="Same", price=599, mrp=599)["mrp"] == 599
    assert make_product(seller_with_store, title="Blank", price=599, mrp=None)["mrp"] is None
    assert make_product(seller_with_store, title="Zero", price=599, mrp=0)["mrp"] is None


def test_unknown_category_and_condition_fall_back(seller_with_store):
    p = make_product(seller_with_store, title="Odd", category="weapons", condition="mint")
    assert p["category"] == "" and p["condition"] == "new"


def test_products_listed_before_details_existed_still_read(seller_with_store):
    p = make_product(seller_with_store, title="Old listing", **DETAILS)
    raw_execute("UPDATE products SET mrp = NULL, sku = NULL, category = NULL, details = NULL "
                "WHERE product_id = $1", p["product_id"])
    old = _by_id(seller_with_store, p["product_id"])
    assert old["mrp"] is None and old["sku"] == "" and old["category"] == ""
    assert old["condition"] == "new" and old["specs"] == [] and old["highlights"] == []


def test_sku_is_kept_on_the_order(app_client, seller_with_store):
    p = make_product(seller_with_store, title="Picked by code", paymentMethods=["cod"], sku="LAMP-01")
    r = place_order(app_client, seller_with_store.store_slug,
                    [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}],
                    payment_method="cod")
    assert r.status_code == 200, r.text
    row = raw_fetch_one("SELECT items FROM orders WHERE store_slug = $1", seller_with_store.store_slug)
    items = json.loads(row["items"]) if isinstance(row["items"], str) else row["items"]
    assert items[0]["sku"] == "LAMP-01"


def test_structured_data_carries_details_and_cannot_break_out():
    store = {"name": "Neel", "slug": "neel"}
    product = {
        "title": "</script><script>alert(1)</script>", "slug": "lamp", "price": 599, "mrp": 999,
        "stock": 3, "description": "", "images": [], "brand": "Neel & Co",
        "condition": "refurbished", "countryOfOrigin": "India",
        "specs": [{"name": "Fabric", "value": "Cotton"}],
    }
    ld = seo.product_jsonld(store, {}, product)
    node = json.loads(ld)[0]
    assert node["brand"]["name"] == "Neel & Co"
    assert node["offers"]["itemCondition"] == "https://schema.org/RefurbishedCondition"
    assert node["offers"]["priceSpecification"]["price"] == "999.00"
    assert node["countryOfOrigin"]["name"] == "India"
    assert node["additionalProperty"] == [{"@type": "PropertyValue", "name": "Fabric", "value": "Cotton"}]

    head = seo.build_head(title="Lamp", description="d",
                          canonical="https://stallwise.in/neel/lamp", jsonld=ld)
    assert head.count("</script>") == 1, "seller text closed the JSON-LD script tag"
    embedded = head.split('<script type="application/ld+json">', 1)[1].rsplit("</script>", 1)[0]
    assert json.loads(embedded)[0]["name"] == product["title"]
