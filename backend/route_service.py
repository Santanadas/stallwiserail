"""Razorpay Route (Partner/Marketplace) helper.

Marketo is the platform parent account and onboards each seller as a Linked
Account (sub-merchant). Buyer payments are split so payouts settle to the
seller's own bank. When Route is not enabled on the platform account (test
keys, feature gate) we transparently fall back to a MOCK linked account so the
onboarding flow works end-to-end and can go live later without code changes.
"""
import os
import logging
import requests
import razorpay

logger = logging.getLogger("marketo.route")

ACCOUNTS_URL = "https://api.razorpay.com/v2/accounts"


def _mock_enabled() -> bool:
    return (os.environ.get("MOCK_ROUTE") or "").lower() == "true"


def _keys():
    kid = os.environ.get("RAZORPAY_KEY_ID") or os.environ.get("RAZORPAY_PLATFORM_KEY_ID")
    ksec = os.environ.get("RAZORPAY_KEY_SECRET") or os.environ.get("RAZORPAY_PLATFORM_KEY_SECRET")
    return kid, ksec


def platform_client():
    kid, ksec = _keys()
    if not kid or not ksec:
        return None, None, None
    return razorpay.Client(auth=(kid, ksec)), kid, ksec


def _route_unavailable(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in [
        "the requested url was not found on the server",
        "feature required for the api call is not enabled",
        "route code support feature not enabled",
        "invalid type: route",
        "not enabled",
        "not authorized to use",
    ])


def _mock_account(reference_id: str) -> dict:
    return {"mode": "mock", "account_id": "mock_acc_" + reference_id, "status": "mock_pending"}


def create_linked_account(payload: dict) -> dict:
    """Returns {mode: razorpay|mock|error, account_id?, status?, detail?}."""
    reference_id = payload["reference_id"]
    kid, ksec = _keys()
    if _mock_enabled() or not kid or not ksec:
        return _mock_account(reference_id)
    try:
        r = requests.post(ACCOUNTS_URL, auth=(kid, ksec), json=payload, timeout=20)
    except Exception as e:
        logger.error(f"Route account network error: {e}")
        return _mock_account(reference_id)
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code in (200, 201) and isinstance(body, dict) and body.get("id"):
        return {"mode": "razorpay", "account_id": body["id"], "status": body.get("status", "created")}
    err = body.get("error", {}) if isinstance(body, dict) else {}
    desc = err.get("description", "") or (r.text if r.text else "")
    if _route_unavailable(desc) or r.status_code in (401, 403, 404):
        logger.warning(f"Route unavailable ({r.status_code}: {desc[:120]}); using mock linked account")
        return _mock_account(reference_id)
    return {"mode": "error", "status_code": r.status_code, "detail": desc or "Could not create linked account"}
