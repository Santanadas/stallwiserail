"""Razorpay Route (Partner / Marketplace) onboarding + payout helper.

Stall Wise is the platform parent account. Each seller is onboarded as a Route
linked account (sub-merchant) and their bank account is registered for
settlements, so buyer payments split straight into the seller's bank.

Onboarding flow (Razorpay Route):
  1. POST  /v2/accounts                          -> create linked account (acc_...)
  2. POST  /v2/accounts/:id/products             -> request the "route" product (pcfg_...)
  3. PATCH /v2/accounts/:id/products/:pcfg_id    -> register settlement bank account

When MOCK_ROUTE=true or platform keys are missing we return a mock linked
account so the onboarding UI still works end-to-end without touching Razorpay.
If a live call fails (Route not enabled, validation error, network) we also
fall back to a mock account so seller onboarding never hard-fails.
"""
import os
import logging

import requests
import razorpay

logger = logging.getLogger("stallwise.route")

RZP_BASE = "https://api.razorpay.com/v2"
_TIMEOUT = 15


def _keys():
    kid = os.environ.get("RAZORPAY_KEY_ID") or "rzp_live_TVs3r96Uvj8B1S"
    ksec = os.environ.get("RAZORPAY_KEY_SECRET") or "xM9IugMkJB74bdDbH7UWh3Zi"
    return kid, ksec


def _mock_enabled() -> bool:
    return (os.environ.get("MOCK_ROUTE") or "").lower() == "true"


def platform_client():
    kid, ksec = _keys()
    if not kid or not ksec:
        return None, None, None
    return razorpay.Client(auth=(kid, ksec)), kid, ksec


def _mock_account(reference_id: str) -> dict:
    return {
        "mode": "mock",
        "account_id": "mock_acc_" + reference_id,
        "status": "mock_pending",
        "product_config_id": None,
        "settlement_status": "mock",
    }


def _api(method: str, path: str, json_body: dict) -> requests.Response:
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


def create_linked_account(payload: dict) -> dict:
    """Onboard a seller as a Route linked account and register their settlement
    bank account.

    Expected ``payload`` keys:
      email, phone, reference_id, legal_business_name, business_type,
      contact_name, and (for settlements) beneficiary_name, account_number, ifsc.
      An optional ``profile`` dict overrides the default category.

    Returns ``{mode, account_id, status, product_config_id, settlement_status}``.
    ``mode`` is ``"razorpay"`` for a real linked account, ``"mock"`` otherwise.
    """
    reference_id = payload["reference_id"]
    kid, ksec = _keys()
    if _mock_enabled() or not kid or not ksec:
        return _mock_account(reference_id)

    account_body = {
        "email": payload["email"],
        "phone": payload["phone"],
        "type": "route",
        "reference_id": reference_id,
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
    except Exception as e:
        logger.error(f"Route /accounts network error: {e}")
        return _mock_account(reference_id)

    if r.status_code not in (200, 201):
        logger.warning(f"Route /accounts {r.status_code}: {_err_text(r)}; using provisional account")
        return _mock_account(reference_id)

    account = r.json()
    account_id = account.get("id")
    if not account_id:
        return _mock_account(reference_id)

    status = account.get("status", "created")
    product_config_id = None
    settlement_status = "pending"

    # 2. Request the "route" product configuration for this linked account.
    try:
        pr = _api("POST", f"/accounts/{account_id}/products",
                  {"product_name": "route", "tnc_accepted": True})
        if pr.status_code in (200, 201):
            pcfg = pr.json()
            product_config_id = pcfg.get("id")
            settlement_status = (
                pcfg.get("activation_status") or pcfg.get("state") or "requested"
            )
        else:
            logger.warning(f"Route /products {pr.status_code}: {_err_text(pr)}")
    except Exception as e:
        logger.error(f"Route product request error: {e}")

    # 3. Register the seller's bank account for settlements.
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
            if sr.status_code in (200, 201):
                scfg = sr.json()
                settlement_status = (
                    scfg.get("activation_status") or scfg.get("state") or "configured"
                )
            else:
                logger.warning(f"Route settlement PATCH {sr.status_code}: {_err_text(sr)}")
        except Exception as e:
            logger.error(f"Route settlement config error: {e}")

    return {
        "mode": "razorpay",
        "account_id": account_id,
        "status": status,
        "product_config_id": product_config_id,
        "settlement_status": settlement_status,
    }


def fetch_account_status(account_id: str, product_config_id: str | None = None) -> dict:
    """Poll Razorpay for the current activation / settlement state of a linked
    account. Returns ``{}`` on any error or for mock accounts."""
    if not account_id or account_id.startswith("mock_acc_"):
        return {}
    if _mock_enabled():
        return {}
    out: dict = {}
    try:
        r = _api("GET", f"/accounts/{account_id}", {})
        if r.status_code == 200:
            out["status"] = r.json().get("status")
    except Exception as e:
        logger.error(f"Route account fetch error: {e}")
    if product_config_id:
        try:
            pr = _api("GET", f"/accounts/{account_id}/products/{product_config_id}", {})
            if pr.status_code == 200:
                body = pr.json()
                out["settlement_status"] = (
                    body.get("activation_status") or body.get("state")
                )
        except Exception as e:
            logger.error(f"Route product fetch error: {e}")
    return out
