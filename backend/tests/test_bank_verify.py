"""Bank details are checked before they are saved.

The IFSC has to name a real branch (a free public directory), the account
number has to be typed the same twice, and — when RazorpayX account validation
is switched on — the bank has to confirm the account exists at that IFSC under
the name given. None of these may block a seller when the checking service is
the thing that failed.
"""
import pytest
import requests

import bank_verify
import route_service

# Captured at import, before conftest's autouse fixture replaces the attribute
# for the API tests, so the directory client itself can still be tested.
real_lookup_ifsc = bank_verify.lookup_ifsc

VALID = {
    "legal_business_name": "Studio Craft Enterprises",
    "contact_name": "Aisha Sharma",
    "phone": "9876543210",
    "beneficiary_name": "Aisha Sharma",
    "account_number": "123456789012",
    "account_number_confirm": "123456789012",
    "ifsc": "HDFC0001234",
}

BRANCH = {"ifsc": "HDFC0001234", "bank": "HDFC Bank", "branch": "Nariman Point",
          "city": "Mumbai", "state": "Maharashtra"}


def _onboard(seller, **overrides):
    return seller.post("/api/seller/route/onboard", json={**VALID, **overrides})


@pytest.fixture()
def fake_route(monkeypatch):
    calls = []

    def _create(payload, existing_account_id=None):
        calls.append(payload)
        return {"mode": "razorpay", "account_id": existing_account_id or "acc_TEST123456",
                "status": "created", "product_config_id": "pcfg_1",
                "settlement_status": "activated"}

    monkeypatch.setattr(route_service, "create_linked_account", _create)
    return calls


@pytest.fixture()
def directory(monkeypatch):
    """Control what the IFSC directory says."""
    state = {"answer": BRANCH}

    def _lookup(code):
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(bank_verify, "lookup_ifsc", _lookup)
    return state


@pytest.fixture()
def account_check(monkeypatch):
    """RazorpayX account validation, switched on and answering as told."""
    state = {"answer": bank_verify.AccountCheck("valid", "AISHA SHARMA", "fav_1"), "calls": []}

    def _check(**kw):
        state["calls"].append(kw)
        if isinstance(state["answer"], Exception):
            raise state["answer"]
        return state["answer"]

    monkeypatch.setattr(bank_verify, "account_check_enabled", lambda: True)
    monkeypatch.setattr(bank_verify, "check_account", _check)
    return state


# ------------------------------------------------------------ IFSC ----------
def test_an_ifsc_no_branch_has_is_refused_before_anything_is_saved(
        seller_without_payouts, fake_route, directory):
    directory["answer"] = None
    r = _onboard(seller_without_payouts)
    assert r.status_code == 400
    assert "HDFC0001234" in r.json()["detail"]
    assert fake_route == [], "Razorpay must not be asked to pay into a branch that doesn't exist"
    assert seller_without_payouts.get("/api/seller/route").json() == {"connected": False}


def test_the_bank_the_ifsc_belongs_to_is_shown_back(seller_without_payouts, fake_route, directory):
    body = _onboard(seller_without_payouts).json()
    assert body["bankName"] == "HDFC Bank"
    assert body["bankVerified"] is False, "a real IFSC says nothing about the account"
    assert seller_without_payouts.get("/api/seller/route").json()["bankName"] == "HDFC Bank"


def test_a_directory_outage_does_not_block_the_seller(seller_without_payouts, fake_route, directory):
    directory["answer"] = bank_verify.BankCheckUnavailable("down")
    r = _onboard(seller_without_payouts)
    assert r.status_code == 200, r.text
    assert r.json()["bankName"] == ""
    assert len(fake_route) == 1


def test_the_account_number_has_to_be_typed_the_same_twice(seller_without_payouts, fake_route):
    r = _onboard(seller_without_payouts, account_number_confirm="123456789021")
    assert r.status_code == 400 and "match" in r.json()["detail"]
    assert fake_route == []


def test_the_lookup_endpoint_answers_for_the_form(app_client, seller_without_payouts, directory):
    found = seller_without_payouts.get("/api/seller/route/ifsc/hdfc0001234")
    assert found.status_code == 200 and found.json()["status"] == "found"
    assert found.json()["bank"] == "HDFC Bank"

    directory["answer"] = None
    assert seller_without_payouts.get("/api/seller/route/ifsc/HDFC0001234").json() == {"status": "not_found"}

    directory["answer"] = bank_verify.BankCheckUnavailable("down")
    assert seller_without_payouts.get("/api/seller/route/ifsc/HDFC0001234").json() == {"status": "unknown"}

    assert seller_without_payouts.get("/api/seller/route/ifsc/NOTACODE").status_code == 400
    assert app_client.get("/api/seller/route/ifsc/HDFC0001234").status_code == 401


# ----------------------------------------------------- Account check --------
def test_an_account_the_bank_cannot_find_is_refused(seller_without_payouts, fake_route, account_check):
    account_check["answer"] = bank_verify.AccountCheck("invalid", "", "fav_2")
    r = _onboard(seller_without_payouts)
    assert r.status_code == 400
    assert "9012" in r.json()["detail"] and "HDFC0001234" in r.json()["detail"]
    assert fake_route == []


def test_a_name_the_bank_does_not_hold_is_refused_without_revealing_whose_it_is(
        seller_without_payouts, fake_route, account_check):
    account_check["answer"] = bank_verify.AccountCheck("valid", "RAVI VERMA", "fav_3")
    r = _onboard(seller_without_payouts)
    assert r.status_code == 400
    detail = r.json()["detail"].upper()
    assert "RAVI" not in detail and "VERMA" not in detail, \
        "the form must not become a lookup of who owns an account number"
    assert fake_route == []


def test_a_confirmed_account_is_marked_verified(seller_without_payouts, fake_route, account_check):
    body = _onboard(seller_without_payouts).json()
    assert body["bankVerified"] is True
    assert body["bankVerifiedName"] == "AISHA SHARMA"
    sent = account_check["calls"][0]
    assert (sent["account_number"], sent["ifsc"], sent["name"]) == ("123456789012", "HDFC0001234", "Aisha Sharma")
    assert len(fake_route) == 1


@pytest.mark.parametrize("answer", [
    bank_verify.BankCheckUnavailable("RazorpayX not activated"),
    bank_verify.AccountCheck("pending", "", "fav_4"),
])
def test_no_verdict_from_the_bank_does_not_block_the_seller(
        seller_without_payouts, fake_route, account_check, answer):
    account_check["answer"] = answer
    r = _onboard(seller_without_payouts)
    assert r.status_code == 200, r.text
    assert r.json()["bankVerified"] is False
    assert len(fake_route) == 1


def test_new_details_clear_an_old_verification(seller_without_payouts, fake_route, account_check):
    assert _onboard(seller_without_payouts).json()["bankVerified"] is True
    account_check["answer"] = bank_verify.AccountCheck("pending", "", "fav_5")
    again = _onboard(seller_without_payouts, account_number="999988887777",
                     account_number_confirm="999988887777")
    assert again.status_code == 200, again.text
    assert again.json()["bankVerified"] is False
    assert again.json()["bankLast4"] == "7777"


def test_details_are_verified_even_while_route_is_off(seller_without_payouts, account_check, monkeypatch):
    def _off(payload, existing_account_id=None):
        raise route_service.RouteError("Route feature not enabled for the merchant", upstream_status=400)

    monkeypatch.setattr(route_service, "create_linked_account", _off)
    body = _onboard(seller_without_payouts).json()
    assert body["pending"] is True
    assert body["bankVerified"] is True


def test_account_checks_are_rate_limited_per_seller(seller_without_payouts, fake_route, account_check):
    for _ in range(5):
        assert _onboard(seller_without_payouts).status_code == 200
    r = _onboard(seller_without_payouts)
    assert r.status_code == 429
    assert len(account_check["calls"]) == 5, "every check costs money; the sixth must not be sent"


# ------------------------------------------------ The clients themselves ----
class _Resp:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body
        self.text = ""

    def json(self):
        if self._body is None:
            raise ValueError("no body")
        return self._body


def test_lookup_ifsc_reads_the_directory_and_remembers(monkeypatch):
    bank_verify._ifsc_cache.clear()
    calls = []

    def _get(url, timeout):
        calls.append(url)
        return _Resp(200, {"BANK": "HDFC Bank", "BRANCH": "TULSIANI CHMBRS", "CITY": "MUMBAI",
                           "STATE": "MAHARASHTRA", "IFSC": "HDFC0000001"})

    monkeypatch.setattr(bank_verify.requests, "get", _get)
    first = real_lookup_ifsc("hdfc0000001")
    assert first == {"ifsc": "HDFC0000001", "bank": "HDFC Bank", "branch": "TULSIANI CHMBRS",
                     "city": "MUMBAI", "state": "MAHARASHTRA"}
    assert real_lookup_ifsc("HDFC0000001") == first
    assert calls == ["https://ifsc.razorpay.com/HDFC0000001"]


def test_lookup_ifsc_tells_not_found_from_unavailable(monkeypatch):
    bank_verify._ifsc_cache.clear()
    monkeypatch.setattr(bank_verify.requests, "get", lambda url, timeout: _Resp(404))
    assert real_lookup_ifsc("ABCD0123456") is None

    bank_verify._ifsc_cache.clear()
    monkeypatch.setattr(bank_verify.requests, "get", lambda url, timeout: _Resp(502))
    with pytest.raises(bank_verify.BankCheckUnavailable):
        real_lookup_ifsc("ABCD0123456")

    def _down(url, timeout):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(bank_verify.requests, "get", _down)
    with pytest.raises(bank_verify.BankCheckUnavailable):
        real_lookup_ifsc("ABCD0654321")


def _razorpayx(monkeypatch, final):
    monkeypatch.setenv("RAZORPAYX_ACCOUNT_NUMBER", "7878780080316316")
    monkeypatch.setattr(bank_verify.time, "sleep", lambda s: None)
    sent = []

    def _request(method, url, auth, json, timeout):
        sent.append((method, url.replace(bank_verify.RZP_V1, ""), json))
        if url.endswith("/contacts"):
            return _Resp(200, {"id": "cont_1"})
        if url.endswith("/fund_accounts"):
            return _Resp(200, {"id": "fa_1"})
        if method == "POST":
            return _Resp(200, {"id": "fav_1", "status": "created"})
        return _Resp(200, final)

    monkeypatch.setattr(bank_verify.requests, "request", _request)
    return sent


def test_check_account_waits_for_the_banks_answer(monkeypatch):
    sent = _razorpayx(monkeypatch, {"id": "fav_1", "status": "completed",
                                    "results": {"account_status": "active",
                                                "registered_name": "AISHA SHARMA"}})
    result = bank_verify.check_account(name="Aisha Sharma", account_number="123456789012",
                                       ifsc="HDFC0001234", reference="user_1")
    assert result == bank_verify.AccountCheck("valid", "AISHA SHARMA", "fav_1")
    paths = [(m, p) for m, p, _ in sent]
    assert paths == [("POST", "/contacts"), ("POST", "/fund_accounts"),
                     ("POST", "/fund_accounts/validations"), ("GET", "/fund_accounts/validations/fav_1")]
    validation = sent[2][2]
    assert validation["account_number"] == "7878780080316316"
    assert validation["fund_account"] == {"id": "fa_1"} and validation["amount"] == 100
    assert sent[1][2]["bank_account"] == {"name": "Aisha Sharma", "ifsc": "HDFC0001234",
                                          "account_number": "123456789012"}


def test_check_account_reports_an_account_that_does_not_exist(monkeypatch):
    _razorpayx(monkeypatch, {"id": "fav_1", "status": "completed",
                             "results": {"account_status": "invalid", "registered_name": None}})
    result = bank_verify.check_account(name="A", account_number="1", ifsc="HDFC0001234", reference="u")
    assert result.status == "invalid"


def test_a_failed_validation_is_no_verdict(monkeypatch):
    _razorpayx(monkeypatch, {"id": "fav_1", "status": "failed", "results": {}})
    with pytest.raises(bank_verify.BankCheckUnavailable):
        bank_verify.check_account(name="A", account_number="1", ifsc="HDFC0001234", reference="u")


def test_account_check_is_off_without_razorpayx(monkeypatch):
    monkeypatch.delenv("RAZORPAYX_ACCOUNT_NUMBER", raising=False)
    assert bank_verify.account_check_enabled() is False
    with pytest.raises(bank_verify.BankCheckUnavailable):
        bank_verify.check_account(name="A", account_number="1", ifsc="HDFC0001234", reference="u")


@pytest.mark.parametrize("entered,registered,ok", [
    ("Aisha Sharma", "AISHA SHARMA", True),
    ("Rahul Kumar", "R KUMAR", True),
    ("Rahul Kumar", "KUMAR RAHUL", True),
    ("Mr. Rahul Kumar", "RAHUL K", True),
    ("Aisha Sharma", "", True),                      # some banks return no name
    ("Aisha Sharma", "RAVI VERMA", False),
    ("Sharma Enterprises", "GUPTA ENTERPRISES", False),
    ("Mrs Aisha", "MRS RAVI", False),
])
def test_names_match_is_loose_but_not_meaningless(entered, registered, ok):
    assert bank_verify.names_match(entered, registered) is ok
