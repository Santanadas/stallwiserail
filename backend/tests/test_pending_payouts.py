"""Adding bank details while Route is switched off.

Razorpay answers "Route feature not enabled for the merchant" when the
*platform's* account cannot do Route. That used to come back to the seller as an
error: it asked them to fix something that was never theirs, and threw away
everything they had typed. Their details are fine, so they are now saved — and
connected automatically once Route is on.
"""
import uuid

import pytest

import route_service
import security
import server
from tests.conftest import make_product, raw_execute, raw_fetch_one

VALID = {
    "legal_business_name": "Studio Craft Enterprises",
    "contact_name": "Aisha Sharma",
    "phone": "9876543210",
    "beneficiary_name": "Aisha Sharma",
    "account_number": "123456789012",
    "ifsc": "HDFC0001234",
}


class FakeRoute:
    """Stands in for Razorpay Route; starts switched off."""

    def __init__(self):
        self.enabled = False
        self.reject = False
        self.calls = []

    def __call__(self, payload, existing_account_id=None):
        self.calls.append(dict(payload))
        if not self.enabled:
            raise route_service.RouteError(
                "Route feature not enabled for the merchant", upstream_status=400)
        if self.reject:
            raise route_service.RouteError("The IFSC code is invalid.", upstream_status=400)
        return {"mode": "razorpay", "account_id": existing_account_id or "acc_CONNECTED1",
                "status": "created", "product_config_id": "pcfg_1",
                "settlement_status": "activated"}


@pytest.fixture()
def fake(monkeypatch):
    f = FakeRoute()
    monkeypatch.setattr(route_service, "create_linked_account", f)
    monkeypatch.setattr(server, "_payout_outage", None)
    return f


@pytest.fixture()
def seller(seller_without_payouts):
    return seller_without_payouts


def onboard(seller, **overrides):
    return seller.post("/api/seller/route/onboard", json={**VALID, **overrides})


def seller_id(seller):
    return seller.get("/api/stores/me").json()["sellerId"]


def age(seller):
    """Push the saved row past the background retry window."""
    raw_execute("UPDATE seller_routes SET updated_at = $1 WHERE seller_id = $2",
                "2020-01-01T00:00:00+00:00", seller_id(seller))


def retry(app_client):
    return app_client.portal.call(server.retry_pending_onboarding)


# --- Saving instead of failing -------------------------------------------
def test_adding_bank_details_while_route_is_off_is_not_an_error(seller, fake):
    r = onboard(seller)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pending"] is True
    assert body["detailsSubmitted"] is True
    assert body["payoutsLive"] is False
    assert (body["bankLast4"], body["ifsc"]) == ("9012", "HDFC0001234")


def test_the_saved_account_number_is_encrypted_at_rest(seller, fake):
    onboard(seller)
    row = raw_fetch_one("SELECT account_number_enc FROM seller_routes WHERE seller_id = $1",
                        seller_id(seller))
    assert row["account_number_enc"]
    assert VALID["account_number"] not in row["account_number_enc"]
    assert security.decrypt_secret(row["account_number_enc"]) == VALID["account_number"]


def test_a_waiting_shop_still_cannot_take_online_payment(app_client, seller, fake):
    """Saved is not connected: there is still nowhere to forward the money."""
    onboard(seller)
    make_product(seller, price=500)
    assert app_client.get(f"/api/shop/{seller.store_slug}").json()["acceptsOnline"] is False


def test_the_dashboard_tells_the_seller_there_is_nothing_to_do(seller, fake):
    onboard(seller)
    q = seller.get("/api/dashboard/summary").json()["queue"]
    assert q["bankReady"] is False
    assert q["bankSubmitted"] is True
    assert q["bankAwaitingPlatform"] is True
    assert q["bankNeedsAttention"] is False


def test_the_operator_still_sees_the_outage(app_client, seller, fake):
    onboard(seller)
    health = app_client.get("/health").json()
    assert health["payouts"]["working"] is False


def test_a_seller_with_a_working_account_is_never_downgraded(seller_with_store, fake):
    """Changing details while Route is off must not replace a live account
    with an empty pending one — that would quietly stop payouts they have."""
    before = seller_with_store.get("/api/seller/route").json()
    assert before["payoutsLive"] is True

    r = onboard(seller_with_store, account_number="999988887777")
    assert r.status_code == 503
    assert "unchanged" in r.json()["detail"]

    after = seller_with_store.get("/api/seller/route").json()
    assert after["payoutsLive"] is True
    assert after["accountIdLast4"] == before["accountIdLast4"]
    assert after["pending"] is False


# --- Connecting on its own -----------------------------------------------
def test_refresh_connects_the_account_once_route_is_on(seller, fake):
    onboard(seller)
    fake.enabled = True

    r = seller.post("/api/seller/route/refresh")
    assert r.status_code == 200
    body = r.json()
    assert body["pending"] is False
    assert body["payoutsLive"] is True
    assert body["accountIdLast4"] == "acc_CONNECTED1"[-4:]

    # Built from what the seller saved, decrypted — they typed nothing again.
    sent = fake.calls[-1]
    assert sent["account_number"] == VALID["account_number"]
    assert sent["ifsc"] == VALID["ifsc"]
    assert sent["beneficiary_name"] == VALID["beneficiary_name"]
    assert sent["reference_id"] == seller.store_slug
    assert server._payout_outage is None


def test_refresh_while_route_is_still_off_keeps_it_saved(seller, fake):
    onboard(seller)
    r = seller.post("/api/seller/route/refresh")
    assert r.status_code == 200
    assert r.json()["pending"] is True


def test_the_background_retry_connects_waiting_sellers(app_client, seller, fake):
    onboard(seller)
    age(seller)
    fake.enabled = True
    assert retry(app_client) == 1
    assert seller.get("/api/seller/route").json()["payoutsLive"] is True


def test_a_seller_tried_moments_ago_is_not_retried_yet(app_client, seller, fake):
    onboard(seller)
    fake.enabled = True
    assert retry(app_client) == 0
    assert seller.get("/api/seller/route").json()["pending"] is True


def test_the_retry_stops_at_the_first_route_is_still_off(app_client, make_seller, fake):
    """That answer is the same for everyone; asking again per seller only
    spends Razorpay's rate limit."""
    for i in range(3):
        s = make_seller()
        slug = f"waiting-{i}-{uuid.uuid4().hex[:6]}"
        assert s.post("/api/stores", json={"name": f"Shop {i}", "slug": slug, "bio": ""}).status_code == 200
        onboard(s)
        age(s)
    before = len(fake.calls)
    assert retry(app_client) == 0
    assert len(fake.calls) - before == 1


# --- When Razorpay later says no -----------------------------------------
def test_details_rejected_later_ask_the_seller_to_re_enter(app_client, seller, fake):
    onboard(seller)
    age(seller)
    fake.enabled, fake.reject = True, True
    retry(app_client)

    route = seller.get("/api/seller/route").json()
    assert route["needsAttention"] is True
    assert route["payoutsLive"] is False
    q = seller.get("/api/dashboard/summary").json()["queue"]
    assert q["bankNeedsAttention"] is True
    assert q["bankAwaitingPlatform"] is False

    # A known-bad submission is not retried in the background.
    age(seller)
    calls = len(fake.calls)
    retry(app_client)
    assert len(fake.calls) == calls


def test_re_entering_after_a_rejection_connects(seller, fake):
    onboard(seller)
    fake.enabled, fake.reject = True, True
    seller.post("/api/seller/route/refresh")
    assert seller.get("/api/seller/route").json()["needsAttention"] is True

    fake.reject = False
    r = onboard(seller, ifsc="SBIN0005943")
    assert r.status_code == 200
    body = r.json()
    assert body["payoutsLive"] is True
    assert body["needsAttention"] is False


def test_a_route_error_after_the_account_exists_keeps_the_account(seller, monkeypatch):
    def halfway(payload, existing_account_id=None):
        raise route_service.RouteError("Route feature not enabled for the merchant",
                                       account_id="acc_HALFWAY9", status="created",
                                       upstream_status=400)
    monkeypatch.setattr(route_service, "create_linked_account", halfway)
    monkeypatch.setattr(server, "_payout_outage", None)

    r = onboard(seller)
    assert r.status_code == 200
    body = r.json()
    assert body["pending"] is False
    assert body["accountIdLast4"] == "WAY9"


def test_a_saved_account_can_be_removed(seller, fake):
    onboard(seller)
    seller.delete("/api/seller/route")
    assert seller.get("/api/seller/route").json() == {"connected": False}
