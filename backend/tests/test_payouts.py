"""Whether the seller can actually be paid.

Checkout used to attach the seller's transfer to the Razorpay order, and if
Razorpay rejected it, retry *without* it. That succeeded: the buyer paid, the
order completed, and every rupee landed in the platform account with the seller
never paid and nobody told. A log warning was the only trace.

A shop with nowhere to send money now cannot take an online payment at all.
Cash on delivery is unaffected — that money never passes through us.
"""
import pytest

import route_service
import server
from tests.conftest import link_payout_account, make_product, place_order


def buy_online(app_client, seller, product):
    return place_order(app_client, seller.store_slug,
                       [{"productId": product["product_id"], "quantity": 1,
                         "optionSelections": {}}])


# --- Refusing rather than pocketing it -----------------------------------
def test_a_shop_with_no_payout_account_cannot_sell_online(app_client, seller_without_payouts):
    product = make_product(seller_without_payouts, price=500)
    r = buy_online(app_client, seller_without_payouts, product)
    assert r.status_code == 503
    assert "isn't set up for online payments" in r.json()["detail"]


def test_no_order_and_no_stock_is_taken_when_it_is_refused(app_client, seller_without_payouts):
    product = make_product(seller_without_payouts, price=500, stock=7)
    buy_online(app_client, seller_without_payouts, product)

    assert seller_without_payouts.get("/api/orders").json()["orders"] == []
    assert seller_without_payouts.get("/api/products").json()[0]["stock"] == 7


def test_cash_on_delivery_still_works_without_a_payout_account(app_client, seller_without_payouts):
    """COD money never passes through us, so nothing is being held."""
    product = make_product(seller_without_payouts, price=500, paymentMethods=["cod"])
    r = place_order(app_client, seller_without_payouts.store_slug,
                    [{"productId": product["product_id"], "quantity": 1}],
                    payment_method="cod")
    assert r.status_code == 200
    assert r.json()["amount"] == 500.0


def test_a_rejected_transfer_refuses_the_sale_instead_of_keeping_the_money(
        app_client, seller_with_store, monkeypatch):
    """The original bug: Razorpay rejects the transfer, we retry without it,
    and quietly keep the seller's share."""
    product = make_product(seller_with_store, price=500, stock=4)

    class Boom:
        class order:
            @staticmethod
            def create(payload):
                raise Exception("The transfer account is not activated")

    monkeypatch.setattr(route_service, "platform_client",
                        lambda: (Boom, "rzp_test_fake", "secret"))

    r = buy_online(app_client, seller_with_store, product)
    assert r.status_code == 503
    assert "can't take online payments" in r.json()["detail"]
    assert seller_with_store.get("/api/orders").json()["orders"] == []
    assert seller_with_store.get("/api/products").json()[0]["stock"] == 4


def test_a_linked_shop_sells_normally(app_client, seller_with_store):
    product = make_product(seller_with_store, price=500)
    r = buy_online(app_client, seller_with_store, product)
    assert r.status_code == 200
    assert r.json()["razorpayOrderId"]


# --- Telling the seller the truth ----------------------------------------
def test_submitting_the_form_is_not_the_same_as_being_verified(seller_without_payouts):
    """It used to say "Bank account verified" the moment the form was sent,
    while transfers would still have been rejected."""
    link_payout_account(seller_without_payouts, status="created",
                        settlement_status="under_review")

    route = seller_without_payouts.get("/api/seller/route").json()
    assert route["connected"] is True
    assert route["detailsSubmitted"] is True
    assert route["payoutsLive"] is False

    health = seller_without_payouts.get("/api/dashboard/summary").json()
    assert health["health"]["bankVerified"] is False
    assert health["queue"]["bankReady"] is False


def test_an_activated_account_is_reported_ready(seller_without_payouts):
    link_payout_account(seller_without_payouts, settlement_status="activated")
    assert seller_without_payouts.get("/api/seller/route").json()["payoutsLive"] is True
    assert seller_without_payouts.get("/api/dashboard/summary").json()["queue"]["bankReady"] is True


@pytest.mark.parametrize("state", ["requested", "under_review", "needs_clarification", "pending", ""])
def test_states_before_activation_are_not_ready(seller_without_payouts, state):
    link_payout_account(seller_without_payouts, settlement_status=state)
    assert seller_without_payouts.get("/api/seller/route").json()["payoutsLive"] is False


def test_no_route_at_all_is_not_ready(seller_without_payouts):
    assert seller_without_payouts.get("/api/seller/route").json() == {"connected": False}
    assert seller_without_payouts.get("/api/dashboard/summary").json()["queue"]["bankReady"] is False


# --- The buyer is not offered what will be refused ------------------------
def test_a_shop_that_cannot_be_paid_does_not_offer_online(app_client, seller_without_payouts):
    make_product(seller_without_payouts, price=500)
    assert app_client.get(f"/api/shop/{seller_without_payouts.store_slug}").json()["acceptsOnline"] is False


def test_a_linked_shop_offers_online(app_client, seller_with_store):
    make_product(seller_with_store, price=500)
    assert app_client.get(f"/api/shop/{seller_with_store.store_slug}").json()["acceptsOnline"] is True


def test_the_product_page_says_so_too(app_client, seller_without_payouts):
    product = make_product(seller_without_payouts, price=500)
    body = app_client.get(
        f"/api/shop/{seller_without_payouts.store_slug}/product/{product['slug']}").json()
    assert body["acceptsOnline"] is False


def test_a_pending_verification_still_blocks_online(app_client, seller_without_payouts):
    link_payout_account(seller_without_payouts, settlement_status="under_review")
    make_product(seller_without_payouts, price=500)
    assert app_client.get(f"/api/shop/{seller_without_payouts.store_slug}").json()["acceptsOnline"] is False


def test_the_dashboard_separates_waiting_from_not_started(seller_without_payouts):
    """A seller waiting on Razorpay must not be told to go and do something
    they have already done."""
    before = seller_without_payouts.get("/api/dashboard/summary").json()["queue"]
    assert before["bankReady"] is False and before["bankSubmitted"] is False

    link_payout_account(seller_without_payouts, settlement_status="under_review")
    during = seller_without_payouts.get("/api/dashboard/summary").json()["queue"]
    assert during["bankReady"] is False and during["bankSubmitted"] is True

    link_payout_account(seller_without_payouts, settlement_status="activated")
    after = seller_without_payouts.get("/api/dashboard/summary").json()["queue"]
    assert after["bankReady"] is True and after["bankSubmitted"] is True


# --- The rate we quote has to be the rate we take -------------------------
def test_every_endpoint_quotes_the_rate_that_is_actually_charged(
        app_client, seller_with_store):
    """/api/subscription hardcoded 0% for Pro while checkout took 10% and the
    dashboard reported 10%. A seller could be told two different rates, and
    neither was what left their money."""
    quoted_sub = seller_with_store.get("/api/subscription").json()["commissionRate"]
    quoted_dash = seller_with_store.get("/api/dashboard/summary").json()["metrics"]["commissionRate"]
    assert quoted_sub == quoted_dash

    product = make_product(seller_with_store, price=1000)
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": product["product_id"], "quantity": 1, "optionSelections": {}}])

    created = app_client.fake_razorpay.order.created[-1]
    charged = 1.0 - (created["transfers"][0]["amount"] / created["amount"])
    assert round(charged, 4) == round(quoted_sub, 4), (
        f"quoted {quoted_sub:.0%} but took {charged:.0%}")


def test_a_pro_seller_is_quoted_the_pro_rate(seller_with_store, monkeypatch):
    monkeypatch.setattr(server, "effective_sub_status",
                        lambda user: _immediately("active"))
    assert seller_with_store.get("/api/subscription").json()["commissionRate"] == server.COMMISSION_RATE_PRO


async def _immediately(value):
    return value


# --- One way to get paid, not two ----------------------------------------
def test_a_seller_can_no_longer_hand_us_their_own_gateway_keys(seller_with_store):
    """These stored a seller's live Razorpay key and secret, reported
    "connected", and were read by no checkout — the money went through the
    platform account regardless. Live credentials kept at rest for nothing."""
    gone = [
        seller_with_store.post("/api/seller/razorpay",
                               json={"key_id": "rzp_live_xxx", "key_secret": "supersecret"}),
        seller_with_store.get("/api/seller/razorpay"),
        seller_with_store.delete("/api/seller/razorpay"),
    ]
    for r in gone:
        assert r.status_code in (404, 405), r.status_code


def test_the_bank_details_form_is_the_way_a_seller_gets_paid(
        seller_without_payouts, monkeypatch):
    def _create(payload, existing_account_id=None):
        return {"mode": "razorpay", "account_id": "acc_ONLYWAY", "status": "created",
                "product_config_id": "pcfg_1", "settlement_status": "activated"}

    monkeypatch.setattr(route_service, "create_linked_account", _create)
    seller = seller_without_payouts
    assert seller.get("/api/seller/route").json() == {"connected": False}

    r = seller.post("/api/seller/route/onboard", json={
        "legal_business_name": "Priya Handicrafts",
        "contact_name": "Priya Sharma",
        "phone": "9876543210",
        "beneficiary_name": "Priya Sharma",
        "account_number": "123456789012",
        "ifsc": "HDFC0001234",
    })
    assert r.status_code == 200
    assert r.json()["payoutsLive"] is True
    assert seller.get("/api/dashboard/summary").json()["queue"]["bankReady"] is True


def test_the_store_no_longer_advertises_a_connection_that_did_nothing(seller_with_store):
    store = seller_with_store.get("/api/stores/me").json()
    assert "razorpayConnected" not in store
    assert store["routeConnected"] is True
