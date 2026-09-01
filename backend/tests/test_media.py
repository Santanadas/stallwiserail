"""Product photos have to outlive the container.

Railway rebuilds the filesystem on every deploy and `uploads` is in
.dockerignore, so an image written to disk is gone by the next release — a shop
full of broken pictures and a seller with no idea why. These tests hold the line
that uploads land somewhere that survives.
"""
import io
import shutil

import pytest

import storage
from tests.conftest import make_product

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100fdff03fa0000000049454e44ae426082"
)


def upload(seller, data=PNG, name="photo.png", kind="product"):
    return seller.post(f"/api/uploads/image?kind={kind}",
                       files={"file": (name, io.BytesIO(data), "image/png")})


def test_upload_returns_a_servable_url(seller_with_store, app_client):
    r = upload(seller_with_store)
    assert r.status_code == 200, r.text
    url = r.json()["url"]

    served = app_client.get(url)
    assert served.status_code == 200
    assert served.content == PNG
    assert served.headers["content-type"].startswith("image/png")


def test_the_image_survives_the_container_being_rebuilt(seller_with_store, app_client):
    """The actual bug: the uploads directory does not come back after a deploy."""
    url = upload(seller_with_store).json()["url"]
    assert app_client.get(url).status_code == 200

    # Simulate the deploy: the whole upload directory goes away.
    shutil.rmtree(storage.UPLOAD_DIR, ignore_errors=True)

    again = app_client.get(url)
    assert again.status_code == 200, "the photo did not survive a restart"
    assert again.content == PNG


def test_a_products_photo_still_loads_after_a_rebuild(seller_with_store, app_client):
    url = upload(seller_with_store).json()["url"]
    product = make_product(seller_with_store, images=[url])
    shutil.rmtree(storage.UPLOAD_DIR, ignore_errors=True)

    listed = app_client.get(f"/api/shop/{seller_with_store.store_slug}").json()["products"]
    shown = [p for p in listed if p["product_id"] == product["product_id"]][0]
    assert shown["images"] == [url]
    assert app_client.get(shown["images"][0]).status_code == 200


def test_images_are_cached_hard_because_the_name_never_repeats(seller_with_store, app_client):
    url = upload(seller_with_store).json()["url"]
    first = app_client.get(url)
    assert "immutable" in first.headers["cache-control"]

    etag = first.headers["etag"]
    again = app_client.get(url, headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""


def test_two_uploads_of_the_same_file_do_not_collide(seller_with_store, app_client):
    a = upload(seller_with_store).json()["url"]
    b = upload(seller_with_store).json()["url"]
    assert a != b
    assert app_client.get(a).status_code == 200
    assert app_client.get(b).status_code == 200


def test_a_missing_image_is_a_404_not_a_500(app_client):
    assert app_client.get("/api/files/marketo/uploads/nobody/missing.png").status_code == 404


def test_upload_requires_auth(app_client):
    r = app_client.post("/api/uploads/image",
                        files={"file": ("photo.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 401


def test_only_images_are_accepted(seller_with_store):
    r = upload(seller_with_store, data=b"#!/bin/sh\necho hi\n", name="run.sh")
    assert r.status_code == 400


def test_an_oversized_image_is_refused(seller_with_store):
    r = upload(seller_with_store, data=b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 1))
    assert r.status_code == 400


@pytest.mark.parametrize("path", [
    "..%2f..%2f..%2fetc%2fpasswd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "marketo/uploads/../../../etc/passwd",
])
def test_traversal_in_a_served_path_is_refused(app_client, path):
    """httpx collapses a literal ../ before it leaves the client, so the escape
    has to be encoded to actually reach the route."""
    assert app_client.get(f"/api/files/{path}").status_code == 404


def test_an_avatar_upload_is_recorded_on_the_user(seller_with_store):
    r = upload(seller_with_store, kind="avatar")
    assert r.status_code == 200
    assert seller_with_store.get("/api/auth/me").json()["avatar"] == r.json()["path"]


def test_revalidation_does_not_touch_the_database(seller_with_store, app_client, monkeypatch):
    """A path's bytes never change, so an If-None-Match can be answered from the
    path alone. Reading megabytes back just to say "unchanged" would make a busy
    shop pay for every cached image too."""
    url = upload(seller_with_store).json()["url"]
    etag = app_client.get(url).headers["etag"]

    reads = []
    original = storage.get

    async def counting_get(path):
        reads.append(path)
        return await original(path)

    monkeypatch.setattr(storage, "get", counting_get)
    r = app_client.get(url, headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert reads == [], "a cached image still cost a database read"


def test_the_etag_is_stable_across_requests(seller_with_store, app_client):
    url = upload(seller_with_store).json()["url"]
    assert app_client.get(url).headers["etag"] == app_client.get(url).headers["etag"]


def test_different_images_get_different_etags(seller_with_store, app_client):
    a = upload(seller_with_store).json()["url"]
    b = upload(seller_with_store).json()["url"]
    assert app_client.get(a).headers["etag"] != app_client.get(b).headers["etag"]
