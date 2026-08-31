import pytest

import route_service

VALID = {
    "legal_business_name": "Studio Craft Enterprises",
    "contact_name": "Aisha Sharma",
    "phone": "9876543210",
    "beneficiary_name": "Aisha Sharma",
    "account_number": "123456789012",
    "ifsc": "HDFC0001234",
}


def _onboard(seller, **overrides):
    return seller.post("/api/seller/route/onboard", json={**VALID, **overrides})


@pytest.fixture()
def fake_route(monkeypatch):
    """Stand in for the live Razorpay Route calls."""
    calls = []

    def _create(payload):
        calls.append(payload)
        return {"mode": "razorpay", "account_id": "acc_TEST123456",
                "status": "created", "product_config_id": "pcfg_1",
                "settlement_status": "activated"}

    monkeypatch.setattr(route_service, "create_linked_account", _create)
    return calls


def test_requires_a_store_first(make_seller, fake_route):
    r = _onboard(make_seller())
    assert r.status_code == 400 and "shop handle" in r.json()["detail"].lower()


def test_successful_onboarding_stores_bank_details(seller_with_store, fake_route):
    r = _onboard(seller_with_store)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["connected"] is True
    assert body["payoutsLive"] is True
    assert body["bankLast4"] == "9012"
    assert body["ifsc"] == "HDFC0001234"
    assert body["settlementStatus"] == "activated"

    # The bank details actually reach Razorpay — that was the original bug.
    sent = fake_route[0]
    assert sent["account_number"] == "123456789012"
    assert sent["ifsc"] == "HDFC0001234"
    assert sent["beneficiary_name"] == "Aisha Sharma"


def test_account_number_is_not_echoed_back(seller_with_store, fake_route):
    body = _onboard(seller_with_store).json()
    assert "123456789012" not in str(body), "full account number must never be returned"


@pytest.mark.parametrize("field,value", [
    ("ifsc", "BADCODE"),
    ("ifsc", "hdfc1001234"),      # 5th char must be 0
    ("account_number", "abc123"),
    ("account_number", "123"),     # too short
    ("account_number", ""),
    ("beneficiary_name", ""),
])
def test_invalid_bank_details_rejected_before_hitting_razorpay(
        seller_with_store, fake_route, field, value):
    r = _onboard(seller_with_store, **{field: value})
    assert r.status_code == 400, f"{field}={value!r} was accepted"
    assert fake_route == [], "must not call Razorpay with invalid details"


def test_route_error_surfaces_as_502(seller_with_store, monkeypatch):
    def _boom(payload):
        raise route_service.RouteError("Route is not enabled on this account.")
    monkeypatch.setattr(route_service, "create_linked_account", _boom)

    r = _onboard(seller_with_store)
    assert r.status_code == 502
    assert "not enabled" in r.json()["detail"].lower()


def test_get_and_disconnect_route(seller_with_store, fake_route):
    assert seller_with_store.get("/api/seller/route").json() == {"connected": False}
    _onboard(seller_with_store)
    assert seller_with_store.get("/api/seller/route").json()["connected"] is True
    assert seller_with_store.get("/api/stores/me").json()["routeConnected"] is True

    seller_with_store.delete("/api/seller/route")
    assert seller_with_store.get("/api/seller/route").json() == {"connected": False}


def test_onboarding_requires_auth(app_client):
    assert app_client.post("/api/seller/route/onboard", json=VALID).status_code == 401


def test_checkout_attaches_transfer_once_route_is_live(app_client, seller_with_store, fake_route):
    from conftest import make_product, place_order
    _onboard(seller_with_store)
    p = make_product(seller_with_store, price=1000)
    place_order(app_client, seller_with_store.store_slug,
                [{"productId": p["product_id"], "quantity": 1, "optionSelections": {}}])

    created = app_client.fake_razorpay.order.created[-1]
    transfers = created.get("transfers")
    assert transfers, "a live route must split the payment"
    assert transfers[0]["account"] == "acc_TEST123456"
    assert transfers[0]["amount"] == 90000, "seller gets 90% of 1000 INR in paise"


# ------------------- route_service internals (real code, faked HTTP layer)
class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text or (str(payload) if payload else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


ACCOUNT_PAYLOAD = {
    "email": "s@example.com", "phone": "9876543210", "reference_id": "shop",
    "legal_business_name": "Co", "business_type": "individual", "contact_name": "A B",
    "beneficiary_name": "A B", "account_number": "123456789012", "ifsc": "HDFC0001234",
}


def test_create_linked_account_happy_path_registers_settlements(monkeypatch):
    seen = []

    def _api(method, path, json_body=None):
        seen.append((method, path, json_body))
        if path == "/accounts":
            return _Resp(200, {"id": "acc_1", "status": "created"})
        if path.endswith("/products"):
            return _Resp(200, {"id": "pcfg_1", "activation_status": "requested"})
        return _Resp(200, {"activation_status": "activated"})

    monkeypatch.setattr(route_service, "_api", _api)
    out = route_service.create_linked_account(ACCOUNT_PAYLOAD)

    assert out == {"mode": "razorpay", "account_id": "acc_1", "status": "created",
                   "product_config_id": "pcfg_1", "settlement_status": "activated"}
    methods = [m for m, _, _ in seen]
    assert methods == ["POST", "POST", "PATCH"], "must create, request route, then set bank"
    settlements = seen[-1][2]["settlements"]
    assert settlements["account_number"] == "123456789012"
    assert settlements["ifsc_code"] == "HDFC0001234"


def test_create_linked_account_raises_when_route_not_enabled(monkeypatch):
    monkeypatch.setattr(route_service, "_api", lambda *a, **k: _Resp(
        400, {"error": {"description": "Route is not enabled for this account"}}))
    with pytest.raises(route_service.RouteError, match="not enabled"):
        route_service.create_linked_account(ACCOUNT_PAYLOAD)


def test_create_linked_account_raises_on_network_failure(monkeypatch):
    import requests

    def _boom(*a, **k):
        raise requests.RequestException("connection reset")

    monkeypatch.setattr(route_service, "_api", _boom)
    with pytest.raises(route_service.RouteError, match="Could not reach"):
        route_service.create_linked_account(ACCOUNT_PAYLOAD)


def test_create_linked_account_raises_when_bank_details_rejected(monkeypatch):
    def _api(method, path, json_body=None):
        if path == "/accounts":
            return _Resp(200, {"id": "acc_1", "status": "created"})
        if path.endswith("/products"):
            return _Resp(200, {"id": "pcfg_1"})
        return _Resp(400, {"error": {"description": "Invalid IFSC code"}})

    monkeypatch.setattr(route_service, "_api", _api)
    with pytest.raises(route_service.RouteError, match="Invalid IFSC"):
        route_service.create_linked_account(ACCOUNT_PAYLOAD)


def test_missing_platform_keys_raise_rather_than_silently_mock(monkeypatch):
    monkeypatch.setattr(route_service, "_keys", lambda: ("", ""))
    with pytest.raises(route_service.RouteError, match="not configured"):
        route_service.create_linked_account(ACCOUNT_PAYLOAD)


def test_fetch_account_status_is_safe_on_error(monkeypatch):
    monkeypatch.setattr(route_service, "_api", lambda *a, **k: _Resp(500, None, "boom"))
    assert route_service.fetch_account_status("acc_1", "pcfg_1") == {}
    assert route_service.fetch_account_status("") == {}
