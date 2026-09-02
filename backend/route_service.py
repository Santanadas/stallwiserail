"""Razorpay Route (Partner / Marketplace) onboarding + payout helper.

Stall Wise is the platform parent account. Each seller is onboarded as a Route
linked account (sub-merchant) and their bank account is registered for
settlements, so buyer payments split straight into the seller's bank.

Onboarding flow (Razorpay Route):
  1. POST  /v2/accounts                          -> create linked account (acc_...)
  2. POST  /v2/accounts/:id/products             -> request the "route" product (pcfg_...)
  3. PATCH /v2/accounts/:id/products/:pcfg_id    -> register settlement bank account

Live-only: any failure (Route not enabled, validation error, network) raises
``RouteError`` so the caller can surface the real reason to the seller.
"""
import os
import logging

import requests
import razorpay

logger = logging.getLogger("stallwise.route")

RZP_BASE = "https://api.razorpay.com/v2"
# Onboarding makes three of these calls back to back inside one HTTP request.
# At 15s each that is a 45-second worst case, long enough for a proxy in front
# of us to give up and hand the seller a gateway error page instead of the real
# reason. Ten keeps the whole sequence under half a minute.
_TIMEOUT = float(os.environ.get("RAZORPAY_TIMEOUT", "10"))


class RouteError(Exception):
    """Raised when Razorpay Route onboarding cannot be completed.

    Carries whatever was created before the failure. Onboarding is three
    Razorpay calls, and the account from step 1 exists whether or not steps 2
    and 3 land — so the caller has to be able to save it. Without that, a
    retry re-posts /accounts with the same reference_id, Razorpay rejects the
    duplicate, and the seller can never onboard again.
    """

    def __init__(self, message: str, account_id: str | None = None,
                 product_config_id: str | None = None,
                 status: str | None = None, settlement_status: str | None = None,
                 upstream_status: int | None = None):
        super().__init__(message)
        self.account_id = account_id
        self.product_config_id = product_config_id
        self.status = status
        self.settlement_status = settlement_status
        # What Razorpay answered, so the caller can tell "your IFSC is wrong"
        # from "the gateway is down". They need very different responses: one
        # is the seller's to fix, the other is ours.
        self.upstream_status = upstream_status

    @property
    def is_sellers_to_fix(self) -> bool:
        return self.upstream_status is not None and 400 <= self.upstream_status < 500


def _keys():
    kid = (os.environ.get("RAZORPAY_KEY_ID") or "").strip()
    ksec = (os.environ.get("RAZORPAY_KEY_SECRET") or "").strip()
    return kid, ksec


# The Razorpay SDK never passes a timeout to requests — Client.request catches
# requests.exceptions.Timeout but nothing ever sets one — and it retries on top.
# A slow or unreachable gateway therefore hangs the call indefinitely. Because
# every Razorpay call runs inside asyncio.to_thread, hung calls hold threads in
# the default executor; exhaust that pool and every other threaded operation
# stalls with it — image serving and, on the SQLite path, database queries. That
# is how one slow payment request stops the whole origin answering and Cloudflare
# reports a 520. Bound it well under Cloudflare's 100-second ceiling.
RAZORPAY_TIMEOUT = float(os.environ.get("RAZORPAY_TIMEOUT", "15"))


class _TimeoutSession(requests.Session):
    """A requests Session that applies a default timeout to every call."""

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", RAZORPAY_TIMEOUT)
        return super().request(*args, **kwargs)


def razorpay_client(kid: str, ksec: str):
    """Build a Razorpay client that cannot hang forever."""
    return razorpay.Client(auth=(kid, ksec), session=_TimeoutSession(), max_retries=1)


def platform_client():
    kid, ksec = _keys()
    if not kid or not ksec:
        return None, None, None
    return razorpay_client(kid, ksec), kid, ksec


def _api(method: str, path: str, json_body: dict | None = None) -> requests.Response:
    kid, ksec = _keys()
    return requests.request(
        method,
        f"{RZP_BASE}{path}",
        auth=(kid, ksec),
        json=json_body or None,
        timeout=_TIMEOUT,
        headers={"Content-Type": "application/json"},
    )


def _err_text(resp: requests.Response) -> str:
    try:
        body = resp.json()
        return (body.get("error") or {}).get("description") or resp.text
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"


def create_linked_account(payload: dict, existing_account_id: str | None = None) -> dict:
    """Onboard a seller as a Route linked account and register their settlement
    bank account.

    Expected ``payload`` keys:
      email, phone, reference_id, legal_business_name, business_type,
      contact_name, beneficiary_name, account_number, ifsc.
      An optional ``profile`` dict overrides the default category.

    Returns ``{mode, account_id, status, product_config_id, settlement_status}``
    (``mode`` is always ``"razorpay"``). Raises ``RouteError`` on failure.
    """
    kid, ksec = _keys()
    if not kid or not ksec:
        raise RouteError("Platform payment gateway is not configured.")

    # Resuming. Razorpay enforces a unique reference_id per linked account, so
    # re-creating one for a seller who already has it fails permanently. If the
    # last attempt got as far as an account, carry on from there.
    if existing_account_id:
        logger.info("resuming Route onboarding for existing account %s", existing_account_id)
        return _configure_route_product(existing_account_id, payload, status="created")

    account_body = {
        "email": payload["email"],
        "phone": payload["phone"],
        "type": "route",
        "reference_id": payload["reference_id"],
        "legal_business_name": payload["legal_business_name"],
        "business_type": (payload.get("business_type") or "individual"),
        "contact_name": payload["contact_name"],
        "profile": payload.get("profile") or {
            "category": "ecommerce",
            "subcategory": "marketplace",
        },
    }

    try:
        r = _api("POST", "/accounts", account_body)
    except requests.RequestException as e:
        logger.error(f"Route /accounts network error: {e}")
        raise RouteError("Could not reach the payment gateway. Please try again.")

    if r.status_code not in (200, 201):
        msg = _err_text(r)
        logger.warning(f"Route /accounts {r.status_code}: {msg}")
        raise RouteError(msg or "Razorpay rejected the account details.",
                         upstream_status=r.status_code)

    account = r.json()
    account_id = account.get("id")
    if not account_id:
        raise RouteError("Razorpay did not return a linked account id.")

    status = account.get("status", "created")
    return _configure_route_product(account_id, payload, status=status)


def _configure_route_product(account_id: str, payload: dict, status: str = "created") -> dict:
    """Steps 2 and 3: request the Route product, then register the bank account.

    Separate from account creation so a retry can resume here. Every failure
    below reports the account_id back on the exception, so the caller can save
    what exists rather than orphan it at Razorpay.
    """
    product_config_id = None
    settlement_status = "pending"

    try:
        pr = _api("POST", f"/accounts/{account_id}/products",
                  {"product_name": "route", "tnc_accepted": True})
    except requests.RequestException as e:
        logger.error(f"Route product request error: {e}")
        raise RouteError("Could not reach the payment gateway. Please try again.",
                         account_id=account_id, status=status)

    if pr.status_code in (200, 201):
        pcfg = pr.json()
        product_config_id = pcfg.get("id")
        settlement_status = pcfg.get("activation_status") or pcfg.get("state") or "requested"
    else:
        msg = _err_text(pr)
        logger.warning(f"Route /products {pr.status_code}: {msg}")
        # Already requested on a previous attempt is not a failure — find it.
        product_config_id = _find_route_product(account_id)
        if not product_config_id:
            raise RouteError(msg or "Could not enable Route for this account.",
                             account_id=account_id, status=status,
                             upstream_status=pr.status_code)

    if product_config_id and payload.get("account_number") and payload.get("ifsc"):
        try:
            sr = _api(
                "PATCH",
                f"/accounts/{account_id}/products/{product_config_id}",
                {
                    "settlements": {
                        "account_number": str(payload["account_number"]).strip(),
                        "ifsc_code": str(payload["ifsc"]).strip().upper(),
                        "beneficiary_name": (
                            payload.get("beneficiary_name") or payload["contact_name"]
                        ),
                    },
                    "tnc_accepted": True,
                },
            )
        except requests.RequestException as e:
            logger.error(f"Route settlement config error: {e}")
            raise RouteError("Could not reach the payment gateway. Please try again.",
                             account_id=account_id, product_config_id=product_config_id,
                             status=status, settlement_status=settlement_status)

        if sr.status_code in (200, 201):
            scfg = sr.json()
            settlement_status = scfg.get("activation_status") or scfg.get("state") or "configured"
        else:
            logger.warning(f"Route settlement PATCH {sr.status_code}: {_err_text(sr)}")
            raise RouteError(_err_text(sr) or "Razorpay rejected the bank account details.",
                             account_id=account_id, product_config_id=product_config_id,
                             status=status, settlement_status=settlement_status,
                             upstream_status=sr.status_code)

    return {
        "mode": "razorpay",
        "account_id": account_id,
        "status": status,
        "product_config_id": product_config_id,
        "settlement_status": settlement_status,
    }


def _find_route_product(account_id: str) -> str | None:
    """The Route product config this account already has, if any."""
    try:
        r = _api("GET", f"/accounts/{account_id}/products")
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        items = r.json()
        if isinstance(items, dict):
            items = items.get("items") or []
        for item in items:
            if item.get("product_name") == "route":
                return item.get("id")
    except Exception:
        pass
    return None


def fetch_account_status(account_id: str, product_config_id: str | None = None) -> dict:
    """Poll Razorpay for the current activation / settlement state of a linked
    account. Returns ``{}`` on any error."""
    if not account_id:
        return {}
    out: dict = {}
    try:
        r = _api("GET", f"/accounts/{account_id}")
        if r.status_code == 200:
            out["status"] = r.json().get("status")
    except Exception as e:
        logger.error(f"Route account fetch error: {e}")
    if product_config_id:
        try:
            pr = _api("GET", f"/accounts/{account_id}/products/{product_config_id}")
            if pr.status_code == 200:
                body = pr.json()
                out["settlement_status"] = (
                    body.get("activation_status") or body.get("state")
                )
        except Exception as e:
            logger.error(f"Route product fetch error: {e}")
    return out
