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
_TIMEOUT = 15


class RouteError(Exception):
    """Raised when Razorpay Route onboarding cannot be completed."""


def _keys():
    kid = os.environ.get("RAZORPAY_KEY_ID") or "rzp_live_TVs3r96Uvj8B1S"
    ksec = os.environ.get("RAZORPAY_KEY_SECRET") or "xM9IugMkJB74bdDbH7UWh3Zi"
    return kid, ksec


def platform_client():
    kid, ksec = _keys()
    if not kid or not ksec:
        return None, None, None
    return razorpay.Client(auth=(kid, ksec)), kid, ksec


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


def create_linked_account(payload: dict) -> dict:
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
        raise RouteError(msg or "Razorpay rejected the account details.")

    account = r.json()
    account_id = account.get("id")
    if not account_id:
        raise RouteError("Razorpay did not return a linked account id.")

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
            raise RouteError(_err_text(pr) or "Could not enable Route for this account.")
    except requests.RequestException as e:
        logger.error(f"Route product request error: {e}")
        raise RouteError("Could not reach the payment gateway. Please try again.")

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
                raise RouteError(_err_text(sr) or "Razorpay rejected the bank account details.")
        except requests.RequestException as e:
            logger.error(f"Route settlement config error: {e}")
            raise RouteError("Could not reach the payment gateway. Please try again.")

    return {
        "mode": "razorpay",
        "account_id": account_id,
        "status": status,
        "product_config_id": product_config_id,
        "settlement_status": settlement_status,
    }


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
