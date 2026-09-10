"""Checking a seller's bank details before they are saved.

Two layers, because only one of them is free:

1. **The IFSC exists.** Razorpay publishes the RBI branch directory as an open
   API (ifsc.razorpay.com, no key needed). A code that isn't in it cannot receive
   money, so it is refused up front — and the bank and branch a real code names
   are shown back to the seller, which is how most people notice a mistyped
   digit.

2. **The account exists at that IFSC, in that name.** Only a bank can answer
   this, by crediting the account ("penny drop"). Razorpay sells that as
   RazorpayX Fund Account Validation: ₹1 goes to the account and the bank reports
   whether it landed and whose name the account is in. It needs RazorpayX
   activated on the platform account and costs money per check, so it only runs
   when RAZORPAYX_ACCOUNT_NUMBER is set.

Neither layer may lock a seller out for a failure of ours. When the directory or
RazorpayX can't answer, ``BankCheckUnavailable`` is raised and the caller falls
back to the format checks, leaving Route's own verification before the first
payout as the backstop.
"""
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger("stallwise.bank_verify")

IFSC_API = "https://ifsc.razorpay.com"
RZP_V1 = "https://api.razorpay.com/v1"

_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_IFSC_TIMEOUT = 5.0
_TIMEOUT = float(os.environ.get("RAZORPAY_TIMEOUT", "10"))
# A penny drop over IMPS normally settles in a few seconds. Wait this long inside
# the seller's request, then treat it as undecided rather than hold their browser
# — onboarding already makes up to three Razorpay calls after this.
_VALIDATION_WAIT_SECONDS = 12.0
_POLL_EVERY = 2.0


class BankCheckUnavailable(Exception):
    """The checking service couldn't give an answer — ours to fix, not the seller's."""


# ---------------------------------------------------------------- IFSC ------
# Branch codes change rarely and the directory is a public service, so answers
# are kept for the life of the process. Deploys clear it.
_ifsc_cache: dict = {}
_IFSC_CACHE_MAX = 5000


def lookup_ifsc(ifsc: str) -> Optional[dict]:
    """``{ifsc, bank, branch, city, state}`` for a real branch, ``None`` when no
    branch has this code. Raises ``BankCheckUnavailable`` if the directory can't
    be reached or answers with something unexpected."""
    code = (ifsc or "").strip().upper()
    if not _IFSC_RE.match(code):
        return None
    if code in _ifsc_cache:
        return _ifsc_cache[code]

    try:
        r = requests.get(f"{IFSC_API}/{code}", timeout=_IFSC_TIMEOUT)
    except requests.RequestException as e:
        raise BankCheckUnavailable(f"IFSC directory unreachable: {e}") from e

    if r.status_code == 404:
        result = None
    elif r.status_code == 200:
        try:
            body = r.json()
        except ValueError as e:
            raise BankCheckUnavailable("IFSC directory answered with something that isn't JSON") from e
        if not isinstance(body, dict) or not body.get("BANK"):
            raise BankCheckUnavailable("IFSC directory answer had no bank in it")
        result = {
            "ifsc": body.get("IFSC") or code,
            "bank": body.get("BANK") or "",
            "branch": body.get("BRANCH") or "",
            "city": body.get("CITY") or "",
            "state": body.get("STATE") or "",
        }
    else:
        raise BankCheckUnavailable(f"IFSC directory answered HTTP {r.status_code}")

    if len(_ifsc_cache) >= _IFSC_CACHE_MAX:
        _ifsc_cache.clear()
    _ifsc_cache[code] = result
    return result


# ------------------------------------------------------- Penny drop ---------
@dataclass
class AccountCheck:
    """What the bank said. ``status`` is "valid", "invalid" or "pending" (the
    bank hadn't answered within the wait)."""
    status: str
    registered_name: str = ""
    validation_id: str = ""


def _keys():
    return ((os.environ.get("RAZORPAY_KEY_ID") or "").strip(),
            (os.environ.get("RAZORPAY_KEY_SECRET") or "").strip())


def _payer_account() -> str:
    # The RazorpayX account the ₹1 is sent from — shown on the RazorpayX
    # dashboard as the "account number" of the business's current account.
    return (os.environ.get("RAZORPAYX_ACCOUNT_NUMBER") or "").strip()


def account_check_enabled() -> bool:
    kid, ksec = _keys()
    return bool(_payer_account() and kid and ksec)


def _err_text(resp) -> str:
    try:
        return ((resp.json() or {}).get("error") or {}).get("description") or resp.text
    except Exception:
        return getattr(resp, "text", "") or f"HTTP {resp.status_code}"


def _x(method: str, path: str, body: Optional[dict] = None) -> dict:
    try:
        r = requests.request(method, f"{RZP_V1}{path}", auth=_keys(), json=body,
                             timeout=_TIMEOUT)
    except requests.RequestException as e:
        raise BankCheckUnavailable(f"RazorpayX unreachable: {e}") from e
    if r.status_code not in (200, 201):
        # Every refusal here is treated as "no answer", including ones that name
        # a field: the IFSC has already passed the directory, and RazorpayX not
        # being activated reads much like a bad request. Blocking a seller on a
        # guess would be worse than letting Route verify the account later.
        raise BankCheckUnavailable(f"RazorpayX {method} {path} HTTP {r.status_code}: {_err_text(r)}")
    try:
        return r.json()
    except ValueError as e:
        raise BankCheckUnavailable(f"RazorpayX {path} answered with something that isn't JSON") from e


def check_account(*, name: str, account_number: str, ifsc: str, reference: str) -> AccountCheck:
    """Penny-drop the account: contact → fund account → validation, then wait
    briefly for the bank's answer. Raises ``BankCheckUnavailable`` when there is
    no verdict to act on."""
    if not account_check_enabled():
        raise BankCheckUnavailable("RazorpayX account validation isn't configured")

    contact = _x("POST", "/contacts", {
        "name": (name or "Seller")[:50],
        "type": "vendor",
        "reference_id": (reference or "")[:40],
    })
    fund = _x("POST", "/fund_accounts", {
        "contact_id": contact.get("id"),
        "account_type": "bank_account",
        "bank_account": {"name": (name or "")[:120], "ifsc": ifsc, "account_number": account_number},
    })
    fav = _x("POST", "/fund_accounts/validations", {
        "account_number": _payer_account(),
        "fund_account": {"id": fund.get("id")},
        "amount": 100,
        "currency": "INR",
        "notes": {"purpose": "Stall Wise payout account check"},
    })

    deadline = time.monotonic() + _VALIDATION_WAIT_SECONDS
    while fav.get("status") == "created" and fav.get("id") and time.monotonic() < deadline:
        time.sleep(_POLL_EVERY)
        fav = _x("GET", f"/fund_accounts/validations/{fav['id']}")
    return _verdict(fav)


def _verdict(fav: dict) -> AccountCheck:
    status = fav.get("status")
    results = fav.get("results") or {}
    vid = fav.get("id") or ""
    if status == "completed":
        account_status = results.get("account_status")
        if account_status == "active":
            return AccountCheck("valid", results.get("registered_name") or "", vid)
        if account_status == "invalid":
            return AccountCheck("invalid", "", vid)
    if status == "failed":
        # The validation itself didn't go through (the bank was unreachable,
        # say). That is no verdict on the account.
        raise BankCheckUnavailable(f"account validation {vid} failed without a result")
    return AccountCheck("pending", "", vid)


# ------------------------------------------------------- Name match ---------
# Words that say nothing about who holds the account: titles, and the generic
# half of a business name. "Sharma Enterprises" and "Gupta Enterprises" must not
# match on "ENTERPRISES".
_NOISE = {
    "MR", "MRS", "MS", "MISS", "DR", "SHRI", "SRI", "SMT", "KUMARI", "KUM",
    "AND", "THE", "M/S", "ENTERPRISE", "ENTERPRISES", "TRADERS", "TRADING",
    "STORE", "STORES", "SHOP", "PVT", "PRIVATE", "LTD", "LIMITED", "LLP",
    "COMPANY", "INDIA", "SONS", "INDUSTRIES", "SERVICES", "SOLUTIONS",
}


def _words(text: str) -> set:
    return {w for w in re.findall(r"[A-Z]+", (text or "").upper())
            if len(w) >= 3 and w not in _NOISE}


def names_match(entered: str, registered: str) -> bool:
    """Loose on purpose. Banks hold "R KUMAR" for Rahul Kumar, or "KUMAR RAHUL";
    demand an exact match and genuine sellers bounce. It passes when one real
    word (three letters or more, not a title or a generic business word) is in
    both, or when the bank returned no name at all."""
    if not (registered or "").strip():
        return True
    return bool(_words(entered) & _words(registered))
