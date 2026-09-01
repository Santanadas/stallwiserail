import os
import sys
import json
import re
import uuid
import logging
import hashlib
import hmac
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

import httpx
import razorpay
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, Query, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

import db
import security
import email_service
import storage
import route_service
import seo
import ai_service
import ai_assistant

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
PREMIUM_TIER = "Stall Wise Pro"
FREE_TIER = "Free Plan"
COMMISSION_RATE_FREE = 0.10
COMMISSION_RATE_PRO = 0.10
# "online" = Razorpay checkout (UPI, cards, netbanking, wallets).
# "cod"    = cash collected by the seller on delivery.
PAYMENT_METHODS = ("online", "cod")

# A product at or below this many units shows up in the dashboard action queue.
LOW_STOCK_THRESHOLD = 3
DEFAULT_WINDOW_MIN = 120
OTP_EXPIRY_MIN = 4320  # 3 days
OTP_MAX_ATTEMPTS = 5
AUTH_OTP_EXPIRY_MIN = 10
AUTH_OTP_MAX_ATTEMPTS = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stallwise")

app = FastAPI()
api = APIRouter(prefix="/api")


def now():
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_dt(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def slugify(text: str, fallback: str = "item") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)[:60].strip("-")
    return s or fallback


async def unique_product_slug(store_slug: str, title: str, exclude_id: Optional[str] = None) -> str:
    """A per-store slug for the product's own URL: /{store}/{product}."""
    base = slugify(title, "product")
    candidate = base
    for n in range(2, 60):
        row = await db.fetch_one(
            "SELECT product_id FROM products WHERE store_slug = $1 AND slug = $2",
            store_slug, candidate,
        )
        if not row or (exclude_id and row["product_id"] == exclude_id):
            return candidate
        candidate = f"{base}-{n}"
    return f"{base}-{uuid.uuid4().hex[:6]}"


# ======================= Models =======================
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=6, max_length=128)


class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=2, max_length=60)
    bio: str = Field(default="", max_length=500)
    acceptanceWindowMinutes: int = Field(default=DEFAULT_WINDOW_MIN, ge=1, le=10080)


class StoreUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    acceptanceWindowMinutes: Optional[int] = Field(default=None, ge=1, le=10080)
    deliveryFee: Optional[float] = Field(default=None, ge=0, le=100000)
    freeDeliveryAbove: Optional[float] = Field(default=None, ge=0, le=10000000)
    dispatchDays: Optional[int] = Field(default=None, ge=0, le=60)
    gstin: Optional[str] = Field(default=None, max_length=20)
    hsnCode: Optional[str] = Field(default=None, max_length=12)
    notifyNewOrder: Optional[bool] = None
    notifyDailySummary: Optional[bool] = None
    notifyWeeklyDigest: Optional[bool] = None


class RouteOnboardIn(BaseModel):
    legal_business_name: str = Field(min_length=3, max_length=200)
    contact_name: str = Field(min_length=3, max_length=200)
    phone: str = Field(min_length=8, max_length=15)
    business_type: str = Field(default="individual", max_length=50)
    beneficiary_name: str = Field(default="", max_length=200)
    account_number: str = Field(default="", max_length=34)
    ifsc: str = Field(default="", max_length=11)


class RazorpayIn(BaseModel):
    key_id: str = Field(min_length=5, max_length=100)
    key_secret: str = Field(min_length=8, max_length=150)
    webhook_secret: Optional[str] = Field(default=None, max_length=150)


class OptionIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    priceDelta: float = Field(default=0.0, ge=-1000000.0, le=1000000.0)
    stock: Optional[int] = Field(default=None, ge=0, le=100000)


class OptionGroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    options: List[OptionIn] = Field(min_length=1, max_length=50)


class ProductIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    price: float = Field(gt=0, le=10000000.0)
    stock: Optional[int] = Field(default=None, ge=0, le=100000)
    optionGroups: List[OptionGroupIn] = Field(default_factory=list, max_length=5)
    active: bool = True
    image: Optional[str] = Field(default=None, max_length=500)
    images: List[str] = Field(default_factory=list, max_length=8)
    paymentMethods: List[str] = Field(default_factory=lambda: ["online"], max_length=4)


class AIDescribeIn(BaseModel):
    """Whatever the seller has filled in so far, so Claude can write from it."""
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    keywords: str = Field(default="", max_length=300)
    price: Optional[float] = Field(default=None, gt=0, le=10000000.0)
    stock: Optional[int] = Field(default=None, ge=0, le=100000)
    images: List[str] = Field(default_factory=list, max_length=8)
    optionGroups: List[OptionGroupIn] = Field(default_factory=list, max_length=5)


class AssistantTurnIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(default="", max_length=2000)


class AssistantIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: List[AssistantTurnIn] = Field(default_factory=list, max_length=12)


class AssistantChangeIn(BaseModel):
    """One proposal coming back for the seller to apply.

    Deliberately loose: nothing here is trusted. The apply route looks the
    product up again by owner, drops any key it does not recognise and re-runs
    the same bounds the assistant ran. A client that hand-writes this body gets
    no further than the assistant would have.
    """
    kind: str = Field(pattern="^(product|settings)$")
    productId: Optional[str] = Field(default=None, max_length=64)
    changes: Dict[str, Any] = Field(default_factory=dict)


class AssistantApplyIn(BaseModel):
    proposals: List[AssistantChangeIn] = Field(min_length=1, max_length=10)


class BulkOrderIn(BaseModel):
    orderIds: List[str] = Field(min_length=1, max_length=50)


class OrderItemIn(BaseModel):
    productId: str
    quantity: int = Field(ge=1, le=1000)
    optionSelections: Dict[str, str] = Field(default_factory=dict)


class OrderIn(BaseModel):
    storeSlug: str
    items: List[OrderItemIn] = Field(min_length=1, max_length=50)
    buyerName: str = Field(min_length=1, max_length=100)
    buyerEmail: EmailStr
    buyerPhone: str = Field(min_length=8, max_length=15)
    address: Dict[str, Any] = Field(default_factory=dict)
    paymentMethod: str = Field(default="online", max_length=16)


class OtpIn(BaseModel):
    otp: str = Field(min_length=4, max_length=10)


class VerifyOtpIn(BaseModel):
    otp_id: str
    otp: str = Field(min_length=6, max_length=6)


class ResendOtpIn(BaseModel):
    otp_id: str


class SubCreateIn(BaseModel):
    interval: str  # monthly | yearly


class PayVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class DisputeIn(BaseModel):
    email: EmailStr
    reason: str = Field(min_length=3, max_length=1000)


# ======================= Auth helpers =======================
_IS_DEV = FRONTEND_URL.startswith("http://localhost") or FRONTEND_URL.startswith("http://127.0.0.1")
_COOKIE_SECURE = not _IS_DEV
_COOKIE_SAMESITE = "lax"


def set_jwt_cookies(resp: Response, user_id: str, email: str) -> str:
    access_tok = security.create_access_token(user_id, email)
    refresh_tok = security.create_refresh_token(user_id)
    # 6-month (180 days) access token, 1-year (365 days) refresh token
    resp.set_cookie("access_token", access_tok,
                    httponly=True, secure=_COOKIE_SECURE, samesite="lax", max_age=15552000, path="/")
    resp.set_cookie("refresh_token", refresh_tok,
                    httponly=True, secure=_COOKIE_SECURE, samesite="lax", max_age=31536000, path="/")
    return access_tok


async def public_user(u: Optional[dict]) -> Optional[dict]:
    if not u:
        return None
    store = await db.fetch_one("SELECT store_id, slug, name FROM stores WHERE seller_id = $1", u["user_id"])
    return {
        "user_id": u["user_id"],
        "email": u["email"],
        "name": u.get("name"),
        "role": u.get("role", "seller"),
        "authProvider": u.get("auth_provider") or u.get("authProvider", "password"),
        "subscriptionStatus": u.get("subscription_status") or u.get("subscriptionStatus", "inactive"),
        "picture": u.get("picture"),
        "avatar": u.get("avatar"),
        "created_at": u.get("created_at"),
        "hasStore": bool(store),
        "storeSlug": store["slug"] if store else None,
        "storeName": store["name"] if store else None,
    }


def public_store(s: Optional[dict]) -> Optional[dict]:
    if not s:
        return None
    return {
        "store_id": s["store_id"],
        "sellerId": s.get("seller_id") or s.get("sellerId"),
        "name": s["name"],
        "slug": s["slug"],
        "bio": s.get("bio") or "",
        "logo": s.get("logo"),
        "acceptanceWindowMinutes": s.get("acceptance_window_minutes") or s.get("acceptanceWindowMinutes", DEFAULT_WINDOW_MIN),
        "deliveryFee": float(s.get("delivery_fee") or 0),
        "freeDeliveryAbove": (float(s["free_delivery_above"]) if s.get("free_delivery_above") is not None else None),
        "dispatchDays": (s.get("dispatch_days") if s.get("dispatch_days") is not None else 2),
        "gstin": s.get("gstin") or "",
        "hsnCode": s.get("hsn_code") or "",
        "notifyNewOrder": bool(s.get("notify_new_order", True)),
        "notifyDailySummary": bool(s.get("notify_daily_summary", False)),
        "notifyWeeklyDigest": bool(s.get("notify_weekly_digest", False)),
        "created_at": s["created_at"],
    }


def public_product(p: Optional[dict]) -> Optional[dict]:
    if not p:
        return None
    opts = p.get("option_groups") if "option_groups" in p else p.get("optionGroups", [])
    if isinstance(opts, str):
        try:
            opts = json.loads(opts)
        except Exception:
            opts = []
    imgs = p.get("images", [])
    if isinstance(imgs, str):
        try:
            imgs = json.loads(imgs)
        except Exception:
            imgs = []
    if not imgs and p.get("image"):
        imgs = [p["image"]]
    pays = p.get("payment_methods", p.get("paymentMethods"))
    if isinstance(pays, str):
        try:
            pays = json.loads(pays)
        except Exception:
            pays = None
    pays = [m for m in (pays or []) if m in PAYMENT_METHODS] or ["online"]
    return {
        "product_id": p["product_id"],
        "sellerId": p.get("seller_id") or p.get("sellerId"),
        "storeSlug": p.get("store_slug") or p.get("storeSlug"),
        "title": p["title"],
        "description": p.get("description") or "",
        "price": float(p["price"]),
        "stock": p.get("stock"),
        "optionGroups": opts or [],
        "active": bool(p.get("active", True)),
        "image": (imgs[0] if imgs else p.get("image")),
        "images": imgs or [],
        "paymentMethods": pays,
        "slug": p.get("slug"),
        "created_at": p["created_at"],
    }


def public_order(o: Optional[dict], for_buyer: bool = False) -> Optional[dict]:
    if not o:
        return None
    items = o.get("items", [])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            items = []
    addr = o.get("address", {})
    if isinstance(addr, str):
        try:
            addr = json.loads(addr)
        except Exception:
            addr = {}
    
    out = {
        "order_id": o["order_id"],
        "sellerId": o.get("seller_id") or o.get("sellerId"),
        "storeSlug": o.get("store_slug") or o.get("storeSlug"),
        "buyerName": o.get("buyer_name") or o.get("buyerName"),
        "buyerEmail": o.get("buyer_email") or o.get("buyerEmail"),
        "buyerPhone": o.get("buyer_phone") or o.get("buyerPhone"),
        "address": addr,
        "items": items,
        "subtotal": float(o.get("subtotal", 0)),
        "deliveryFee": float(o.get("delivery_fee") or o.get("deliveryFee", 0)),
        "tax": float(o.get("tax", 0)),
        "amount": float(o.get("amount", 0)),
        "status": o["status"],
        "paymentMethod": (o.get("payment_method") or o.get("paymentMethod") or "online"),
        "razorpayOrderId": o.get("razorpay_order_id") or o.get("razorpayOrderId"),
        "razorpayPaymentId": o.get("razorpay_payment_id") or o.get("razorpayPaymentId"),
        "razorpayKeyId": o.get("razorpay_key_id") or o.get("razorpayKeyId"),
        "otpAttempts": o.get("otp_attempts") or o.get("otpAttempts", 0),
        "otpLocked": bool(o.get("otp_locked") or o.get("otpLocked", False)),
        "otpGeneratedAt": o.get("otp_generated_at") or o.get("otpGeneratedAt"),
        "shippedAt": o.get("shipped_at") or o.get("shippedAt"),
        "paidAt": o.get("paid_at") or o.get("paidAt"),
        "deliveredAt": o.get("delivered_at") or o.get("deliveredAt"),
        "windowExpiresAt": o.get("window_expires_at") or o.get("windowExpiresAt"),
        "disputeRaised": o["status"] == "disputed",
        "disputeReason": o.get("dispute_reason") or o.get("disputeReason"),
        "created_at": o["created_at"],
    }
    if for_buyer and o.get("otp_enc"):
        try:
            out["otp"] = security.decrypt_secret(o["otp_enc"])
        except Exception:
            pass
    return out


async def _resolve_user(token: str):
    if not token:
        return None
    try:
        payload = security.decode_token(token)
        if payload.get("type") == "access":
            u = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", payload["sub"])
            if u:
                return u
    except Exception:
        pass
    sess = await db.fetch_one("SELECT * FROM user_sessions WHERE session_token = $1", token)
    if sess:
        exp = parse_dt(sess.get("expires_at"))
        if exp and exp > now():
            return await db.fetch_one("SELECT * FROM users WHERE user_id = $1", sess["user_id"])
    return None


async def get_current_user(request: Request) -> dict:
    candidates = [request.cookies.get("access_token"), request.cookies.get("session_token")]
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        candidates.append(auth_header[7:])
    for tok in candidates:
        if tok:
            u = await _resolve_user(tok)
            if u:
                return u
    raise HTTPException(status_code=401, detail="Not authenticated")


def get_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# ======================= Auth OTP helper =======================
async def _create_auth_otp(user_id: str, email: str, name: str, purpose: str, password_hash: Optional[str] = None) -> dict:
    otp = security.generate_otp()
    otp_id = new_id("otp")
    created_at = iso(now())
    expires_at = iso(now() + timedelta(minutes=AUTH_OTP_EXPIRY_MIN))
    otp_hash = security.hash_otp(otp)
    _dev_echo = (os.environ.get("DEV_OTP_ECHO") or "").lower() == "true"

    # Clean up any existing pending OTPs for this email and purpose
    await db.execute("DELETE FROM pending_otps WHERE email = $1 AND purpose = $2", email, purpose)

    await db.execute(
        """
        INSERT INTO pending_otps (otp_id, user_id, email, name, password_hash, otp_hash, purpose, attempts, locked, created_at, expires_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, 0, FALSE, $8, $9)
        """,
        otp_id, user_id, email, name, password_hash, otp_hash, purpose, created_at, expires_at
    )
    await email_service.send_auth_otp_email(email, name, otp)
    out = {"otp_id": otp_id}
    if _dev_echo:
        logger.warning("DEV_OTP_ECHO is on — OTPs are returned in API responses. Never enable this in production.")
        out["dev_otp"] = otp
    return out


# ======================= Auth routes =======================
@api.post("/auth/register")
async def register(body: RegisterIn, request: Request, response: Response):
    try:
        client_ip = get_client_ip(request)
        if not security.check_rate_limit(f"reg:{client_ip}", max_requests=30, window_seconds=600):
            raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")
        email = body.email.lower().strip()
        existing = await db.fetch_one("SELECT user_id FROM users WHERE email = $1", email)
        if existing:
            raise HTTPException(status_code=400, detail="This email is already registered. Please go to Login.")
        
        user_id = new_id("user")
        clean_name = security.sanitize_text(body.name, 100)
        password_hash = security.hash_password(body.password)

        # Do NOT insert into users table until OTP is verified
        otp_info = await _create_auth_otp(user_id, email, clean_name, "register", password_hash=password_hash)
        return {"pendingOtp": True, "email": email, "otpId": otp_info["otp_id"], "devOtp": otp_info.get("dev_otp")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database or server error: {str(e)}")


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    try:
        email = body.email.lower().strip()
        client_ip = get_client_ip(request)
        ident = f"{client_ip}:{email}"
        att = await db.fetch_one("SELECT * FROM login_attempts WHERE identifier = $1", ident)
        if att and att.get("count", 0) >= 10:
            locked_until = parse_dt(att.get("locked_until"))
            if locked_until and locked_until > now():
                raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
        user = await db.fetch_one("SELECT * FROM users WHERE email = $1", email)
        if not user or not user.get("password_hash") or not security.verify_password(body.password, user["password_hash"]):
            await db.execute(
                """
                INSERT INTO login_attempts (identifier, count, locked_until)
                VALUES ($1, 1, $2)
                ON CONFLICT (identifier) DO UPDATE
                SET count = login_attempts.count + 1, locked_until = EXCLUDED.locked_until
                """,
                ident, iso(now() + timedelta(minutes=15))
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        await db.execute("DELETE FROM login_attempts WHERE identifier = $1", ident)
        otp_info = await _create_auth_otp(user["user_id"], email, user.get("name", ""), "login")
        return {"pendingOtp": True, "email": email, "otpId": otp_info["otp_id"], "devOtp": otp_info.get("dev_otp")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database or server error: {str(e)}")


@api.post("/auth/verify-otp")
async def verify_auth_otp(body: VerifyOtpIn, request: Request, response: Response):
    client_ip = get_client_ip(request)
    if not security.check_rate_limit(f"auth_otp:{client_ip}", max_requests=30, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait.")
    rec = await db.fetch_one("SELECT * FROM pending_otps WHERE otp_id = $1", body.otp_id)
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired verification session")
    if rec.get("locked"):
        raise HTTPException(status_code=423, detail="Too many failed attempts. Please request a new code.")
    exp = parse_dt(rec.get("expires_at"))
    if exp and now() > exp:
        raise HTTPException(status_code=400, detail="Code expired. Please request a new one.")
    if not security.verify_otp(body.otp.strip(), rec["otp_hash"]):
        attempts = rec.get("attempts", 0) + 1
        locked = attempts >= AUTH_OTP_MAX_ATTEMPTS
        await db.execute(
            "UPDATE pending_otps SET attempts = $1, locked = $2 WHERE otp_id = $3",
            attempts, locked, body.otp_id
        )
        if locked:
            raise HTTPException(status_code=423, detail="Too many failed attempts. Please request a new code.")
        raise HTTPException(status_code=400, detail=f"Invalid code ({attempts}/{AUTH_OTP_MAX_ATTEMPTS} attempts)")
    
    # OTP verified!
    purpose = rec.get("purpose", "login")
    if purpose == "register":
        existing = await db.fetch_one("SELECT * FROM users WHERE email = $1", rec["email"])
        if not existing:
            await db.execute(
                """
                INSERT INTO users (user_id, email, name, password_hash, role, auth_provider, subscription_status, created_at)
                VALUES ($1, $2, $3, $4, 'seller', 'password', 'inactive', $5)
                """,
                rec["user_id"], rec["email"], rec.get("name") or "", rec.get("password_hash") or "", iso(now())
            )
            user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", rec["user_id"])
        else:
            user = existing
    else:
        user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", rec["user_id"])

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute("DELETE FROM pending_otps WHERE otp_id = $1", body.otp_id)
    token = set_jwt_cookies(response, user["user_id"], user["email"])
    out = await public_user(user)
    out["token"] = token
    return out


@api.post("/auth/resend-otp")
async def resend_auth_otp(body: ResendOtpIn, request: Request):
    client_ip = get_client_ip(request)
    if not security.check_rate_limit(f"resend_otp:{client_ip}", max_requests=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many resend attempts. Please wait a few minutes.")
    rec = await db.fetch_one("SELECT * FROM pending_otps WHERE otp_id = $1", body.otp_id)
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid verification session")
    otp = security.generate_otp()
    await db.execute(
        """
        UPDATE pending_otps
        SET otp_hash = $1, attempts = 0, locked = FALSE, expires_at = $2
        WHERE otp_id = $3
        """,
        security.hash_otp(otp),
        iso(now() + timedelta(minutes=AUTH_OTP_EXPIRY_MIN)),
        body.otp_id
    )
    user_name = rec.get("name") or ""
    await email_service.send_auth_otp_email(rec["email"], user_name, otp)
    return {"ok": True, "message": "New verification code sent"}


@api.post("/auth/logout")
async def logout(response: Response):
    for c in ("access_token", "refresh_token", "session_token"):
        response.delete_cookie(c, path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return await public_user(user)


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    tok = request.cookies.get("refresh_token")
    auth_header = request.headers.get("Authorization", "")
    if not tok and auth_header.startswith("Bearer "):
        tok = auth_header[7:]
    if not tok:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = security.decode_token(tok)
        if payload.get("type") not in ("refresh", "access"):
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    token = set_jwt_cookies(response, user["user_id"], user["email"])
    out = await public_user(user)
    out["token"] = token
    return out


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn, request: Request):
    client_ip = get_client_ip(request)
    if not security.check_rate_limit(f"forgot:{client_ip}", max_requests=6, window_seconds=900):
        raise HTTPException(status_code=429, detail="Too many password reset attempts. Please try again later.")
    email = body.email.lower().strip()
    user = await db.fetch_one("SELECT * FROM users WHERE email = $1", email)
    if user and (user.get("auth_provider") or user.get("authProvider")) == "password":
        import secrets as _s
        token = _s.token_urlsafe(32)
        await db.execute(
            "INSERT INTO password_reset_tokens (token, user_id, expires_at, used) VALUES ($1, $2, $3, FALSE)",
            token, user["user_id"], iso(now() + timedelta(hours=1))
        )
        link = f"{FRONTEND_URL}/reset-password?token={token}"
        asyncio.create_task(email_service.send_reset_email(email, link))
    return {"ok": True, "message": "If that email exists, a reset link was sent."}


@api.post("/auth/reset-password")
async def reset_password(body: ResetIn, request: Request):
    # Reset tokens are 256-bit, but unlimited guessing is still not something
    # to leave open.
    if not security.check_rate_limit(f"reset:{get_client_ip(request)}", max_requests=10, window_seconds=900):
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")
    rec = await db.fetch_one("SELECT * FROM password_reset_tokens WHERE token = $1", body.token)
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or used token")
    if parse_dt(rec["expires_at"]) < now():
        raise HTTPException(status_code=400, detail="Token expired")
    await db.execute("UPDATE users SET password_hash = $1 WHERE user_id = $2",
                     security.hash_password(body.password), rec["user_id"])
    await db.execute("UPDATE password_reset_tokens SET used = TRUE WHERE token = $1", body.token)
    return {"ok": True}


# ======================= Store routes =======================
async def get_my_store(user):
    s = await db.fetch_one("SELECT * FROM stores WHERE seller_id = $1", user["user_id"])
    return public_store(s)


@api.post("/stores")
async def create_store(body: StoreIn, user=Depends(get_current_user)):
    slug = body.slug.lower().strip()
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Slug must be lowercase letters, numbers and hyphens")
    existing_slug = await db.fetch_one("SELECT store_id FROM stores WHERE slug = $1", slug)
    if existing_slug:
        raise HTTPException(status_code=400, detail="Slug already taken")
    existing_store = await get_my_store(user)
    if existing_store:
        raise HTTPException(status_code=400, detail="You already have a store")
    
    store_id = new_id("store")
    clean_name = security.sanitize_text(body.name, 100)
    clean_bio = security.sanitize_text(body.bio, 500)
    created_at = iso(now())

    await db.execute(
        """
        INSERT INTO stores (store_id, seller_id, name, slug, bio, acceptance_window_minutes, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        store_id, user["user_id"], clean_name, slug, clean_bio, body.acceptanceWindowMinutes, created_at
    )
    return {
        "store_id": store_id, "sellerId": user["user_id"], "name": clean_name,
        "slug": slug, "bio": clean_bio, "acceptanceWindowMinutes": body.acceptanceWindowMinutes,
        "created_at": created_at,
    }


@api.get("/stores/me")
async def my_store(user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        return None
    rp = await db.fetch_one("SELECT key_id FROM seller_gateways WHERE seller_id = $1", user["user_id"])
    store["razorpayConnected"] = bool(rp)
    route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    store["routeConnected"] = bool(route)
    store["routeStatus"] = route.get("status") if route else None
    store["routeMode"] = route.get("mode") if route else None
    return store


@api.put("/stores/me")
async def update_store(body: StoreUpdateIn, user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=404, detail="No store found")
    
    updates = []
    values = []
    idx = 1

    if body.name is not None:
        updates.append(f"name = ${idx}")
        values.append(security.sanitize_text(body.name, 100))
        idx += 1
    if body.bio is not None:
        updates.append(f"bio = ${idx}")
        values.append(security.sanitize_text(body.bio, 500))
        idx += 1
    if body.acceptanceWindowMinutes is not None:
        updates.append(f"acceptance_window_minutes = ${idx}")
        values.append(body.acceptanceWindowMinutes)
        idx += 1
    for field, column, clean in (
        ("deliveryFee", "delivery_fee", float),
        ("freeDeliveryAbove", "free_delivery_above", float),
        ("dispatchDays", "dispatch_days", int),
        ("gstin", "gstin", lambda v: security.sanitize_text(v, 20).upper()),
        ("hsnCode", "hsn_code", lambda v: security.sanitize_text(v, 12)),
        ("notifyNewOrder", "notify_new_order", bool),
        ("notifyDailySummary", "notify_daily_summary", bool),
        ("notifyWeeklyDigest", "notify_weekly_digest", bool),
    ):
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{column} = ${idx}")
            values.append(clean(val))
            idx += 1

    if updates:
        values.append(store["store_id"])
        await db.execute(f"UPDATE stores SET {', '.join(updates)} WHERE store_id = ${idx}", *values)
    
    return await get_my_store(user)


async def effective_sub_status(seller: dict) -> str:
    status = seller.get("subscription_status") or seller.get("subscriptionStatus", "inactive")
    exp = seller.get("subscription_expires_at") or seller.get("subscriptionExpiresAt")
    if status == "active" and exp and parse_dt(exp) < now():
        await db.execute("UPDATE users SET subscription_status = 'inactive' WHERE user_id = $1", seller["user_id"])
        return "inactive"
    return status


@api.get("/shop/{slug}")
async def public_shop(slug: str):
    store = await db.fetch_one("SELECT * FROM stores WHERE slug = $1", slug.lower().strip())
    if not store:
        raise HTTPException(status_code=404, detail="Shop not found")
    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", store["seller_id"])
    rows = await db.fetch_all("SELECT * FROM products WHERE store_slug = $1 AND active = TRUE ORDER BY created_at DESC", slug.lower().strip())
    products = [public_product(r) for r in rows]
    sub_status = await effective_sub_status(seller) if seller else "inactive"
    return {
        "store": {
            "name": store["name"], "slug": store["slug"], "bio": store.get("bio", ""),
        },
        "seller": {
            "name": seller.get("name") if seller else None,
            "avatar": seller.get("avatar") if seller else None,
        },
        "products": products,
        "showAds": sub_status != "active",
        "tier": PREMIUM_TIER if sub_status == "active" else FREE_TIER,
    }


@api.get("/shop/{slug}/product/{product_slug}")
async def public_product_detail(slug: str, product_slug: str):
    """Backs the crawlable /{store}/{product} page."""
    s = slug.lower().strip()
    store = await db.fetch_one("SELECT * FROM stores WHERE slug = $1", s)
    if not store:
        raise HTTPException(status_code=404, detail="Shop not found")
    row = await db.fetch_one(
        "SELECT * FROM products WHERE store_slug = $1 AND slug = $2 AND active = TRUE",
        s, product_slug.lower().strip(),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", store["seller_id"])
    related = await db.fetch_all(
        "SELECT * FROM products WHERE store_slug = $1 AND active = TRUE AND product_id != $2 ORDER BY created_at DESC LIMIT 4",
        s, row["product_id"],
    )
    sub_status = await effective_sub_status(seller) if seller else "inactive"
    return {
        "store": {"name": store["name"], "slug": store["slug"], "bio": store.get("bio", "")},
        "seller": {
            "name": seller.get("name") if seller else None,
            "avatar": seller.get("avatar") if seller else None,
        },
        "product": public_product(row),
        "related": [public_product(r) for r in related],
        "showAds": sub_status != "active",
    }


@api.get("/shops")
async def public_shop_directory(page: int = Query(1, ge=1), limit: int = Query(24, ge=1, le=60)):
    """Public directory of live shops — real, growing, crawlable content."""
    skip = (page - 1) * limit
    total = await db.fetch_val(
        "SELECT COUNT(*) FROM stores WHERE store_id IN (SELECT DISTINCT store_id FROM stores)"
    )
    rows = await db.fetch_all(
        """
        SELECT s.slug, s.name, s.bio, s.created_at, u.avatar,
               (SELECT COUNT(*) FROM products p WHERE p.store_slug = s.slug AND p.active = TRUE) AS product_count
        FROM stores s LEFT JOIN users u ON u.user_id = s.seller_id
        ORDER BY s.created_at DESC LIMIT $1 OFFSET $2
        """,
        limit, skip,
    )
    shops = [
        {
            "slug": r["slug"],
            "name": r["name"],
            "bio": r.get("bio") or "",
            "avatar": r.get("avatar"),
            "productCount": r.get("product_count") or 0,
            "created_at": r.get("created_at"),
        }
        for r in rows
        if (r.get("product_count") or 0) > 0  # don't index empty shops
    ]
    return {"shops": shops, "total": total or 0, "page": page, "limit": limit,
            "pages": max(1, ((total or 0) + limit - 1) // limit)}


# ======================= Uploads / files =======================
ALLOWED_IMG_EXT = {"jpg", "jpeg", "png", "gif", "webp"}


@api.post("/uploads/image")
async def upload_image(file: UploadFile = File(...), kind: str = Query("product"),
                       user=Depends(get_current_user)):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_IMG_EXT:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, GIF or WEBP images are allowed")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 5MB")
    content_type = file.content_type or storage.MIME_TYPES.get(ext, "application/octet-stream")
    path = storage.build_path(user["user_id"], file.filename or f"img.{ext}")
    try:
        result = await asyncio.to_thread(storage.put_object, path, data, content_type)
    except Exception as e:
        logger.error(f"upload failed: {e}")
        raise HTTPException(status_code=502, detail="Upload failed, please try again")
    stored = result.get("path", path)
    if kind == "avatar":
        await db.execute("UPDATE users SET avatar = $1 WHERE user_id = $2", stored, user["user_id"])
    return {"path": stored, "url": f"/api/files/{stored}"}


@api.delete("/uploads/avatar")
async def delete_avatar(user=Depends(get_current_user)):
    await db.execute("UPDATE users SET avatar = NULL WHERE user_id = $1", user["user_id"])
    return {"ok": True}


@api.get("/files/{path:path}")
async def serve_file(path: str):
    try:
        data, content_type = await asyncio.to_thread(storage.get_object, path)
        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": "inline",
            },
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


# ======================= Seller Route (Razorpay Partner) =======================
def _route_public(route: dict) -> dict:
    return {
        "connected": True,
        "mode": route.get("mode"),
        "status": route.get("status"),
        "settlementStatus": route.get("settlement_status"),
        "payoutsLive": route.get("mode") == "razorpay",
        "accountIdLast4": (route.get("account_id") or "")[-4:],
        "beneficiaryName": route.get("beneficiary_name"),
        "ifsc": route.get("ifsc"),
        "bankLast4": route.get("account_number_last4") or ((route.get("account_number") or "")[-4:] if route.get("account_number") else None),
    }


@api.post("/seller/route/onboard")
async def route_onboard(body: RouteOnboardIn, user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=400, detail="Create your shop handle first")
    clean_legal = security.sanitize_text(body.legal_business_name, 200)
    clean_contact = security.sanitize_text(body.contact_name, 200)
    clean_phone = security.sanitize_text(body.phone, 15)
    clean_beneficiary = security.sanitize_text(body.beneficiary_name, 200)
    clean_ifsc = security.sanitize_text(body.ifsc, 11).upper()
    clean_account = security.sanitize_text(body.account_number, 34).strip()
    bank_last4 = clean_account[-4:] if len(clean_account) >= 4 else None

    if not clean_account or not clean_ifsc or not clean_beneficiary:
        raise HTTPException(status_code=400, detail="Beneficiary name, account number and IFSC are all required for direct payouts")
    if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", clean_ifsc):
        raise HTTPException(status_code=400, detail="That IFSC code doesn't look valid (e.g. HDFC0001234)")
    if not re.match(r"^\d{6,18}$", clean_account):
        raise HTTPException(status_code=400, detail="Bank account number must be 6–18 digits")

    payload = {
        "email": user["email"], "phone": clean_phone,
        "reference_id": store["slug"], "legal_business_name": clean_legal,
        "business_type": body.business_type, "contact_name": clean_contact,
        "beneficiary_name": clean_beneficiary, "account_number": clean_account, "ifsc": clean_ifsc,
        "profile": {"category": "ecommerce", "subcategory": "marketplace"},
    }
    try:
        result = await asyncio.to_thread(route_service.create_linked_account, payload)
    except route_service.RouteError as e:
        raise HTTPException(status_code=502, detail=str(e))

    account_number_enc = security.encrypt_secret(clean_account) if clean_account else None
    updated_at = iso(now())

    await db.execute(
        """
        INSERT INTO seller_routes (seller_id, store_slug, account_id, mode, status, legal_business_name, contact_name, phone, beneficiary_name, account_number_enc, account_number_last4, ifsc, product_config_id, settlement_status, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        ON CONFLICT (seller_id) DO UPDATE SET
            store_slug = EXCLUDED.store_slug, account_id = EXCLUDED.account_id, mode = EXCLUDED.mode,
            status = EXCLUDED.status, legal_business_name = EXCLUDED.legal_business_name,
            contact_name = EXCLUDED.contact_name, phone = EXCLUDED.phone, beneficiary_name = EXCLUDED.beneficiary_name,
            account_number_enc = EXCLUDED.account_number_enc, account_number_last4 = EXCLUDED.account_number_last4,
            ifsc = EXCLUDED.ifsc, product_config_id = EXCLUDED.product_config_id,
            settlement_status = EXCLUDED.settlement_status, updated_at = EXCLUDED.updated_at
        """,
        user["user_id"], store["slug"], result["account_id"], result["mode"], result["status"],
        clean_legal, clean_contact, clean_phone, clean_beneficiary, account_number_enc, bank_last4, clean_ifsc,
        result.get("product_config_id"), result.get("settlement_status"), updated_at
    )
    saved = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    return _route_public(saved)


@api.get("/seller/route")
async def get_route(user=Depends(get_current_user)):
    route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    if not route:
        return {"connected": False}
    return _route_public(route)


@api.post("/seller/route/refresh")
async def refresh_route(user=Depends(get_current_user)):
    route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    if not route:
        raise HTTPException(status_code=404, detail="No payout account connected")
    fresh = await asyncio.to_thread(
        route_service.fetch_account_status, route.get("account_id"), route.get("product_config_id")
    )
    if fresh:
        await db.execute(
            "UPDATE seller_routes SET status = $1, settlement_status = $2, updated_at = $3 WHERE seller_id = $4",
            fresh.get("status") or route.get("status"),
            fresh.get("settlement_status") or route.get("settlement_status"),
            iso(now()), user["user_id"],
        )
        route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    return _route_public(route)


@api.delete("/seller/route")
async def disconnect_route(user=Depends(get_current_user)):
    await db.execute("DELETE FROM seller_routes WHERE seller_id = $1", user["user_id"])
    return {"connected": False}


# ======================= Seller gateway =======================
@api.post("/seller/razorpay")
async def connect_razorpay(body: RazorpayIn, user=Depends(get_current_user)):
    key_secret_enc = security.encrypt_secret(body.key_secret)
    webhook_secret_enc = security.encrypt_secret(body.webhook_secret) if body.webhook_secret else None
    await db.execute(
        """
        INSERT INTO seller_gateways (seller_id, key_id, key_secret_enc, webhook_secret_enc, enabled, created_at)
        VALUES ($1, $2, $3, $4, TRUE, $5)
        ON CONFLICT (seller_id) DO UPDATE SET
            key_id = EXCLUDED.key_id, key_secret_enc = EXCLUDED.key_secret_enc,
            webhook_secret_enc = EXCLUDED.webhook_secret_enc, enabled = TRUE
        """,
        user["user_id"], body.key_id, key_secret_enc, webhook_secret_enc, iso(now())
    )
    return {"connected": True, "key_id_last4": body.key_id[-4:]}


@api.get("/seller/razorpay")
async def get_razorpay(user=Depends(get_current_user)):
    rp = await db.fetch_one("SELECT * FROM seller_gateways WHERE seller_id = $1", user["user_id"])
    if not rp:
        return {"connected": False}
    return {"connected": True, "key_id_last4": rp["key_id"][-4:],
            "webhookConfigured": bool(rp.get("webhook_secret_enc"))}


@api.delete("/seller/razorpay")
async def disconnect_razorpay(user=Depends(get_current_user)):
    await db.execute("DELETE FROM seller_gateways WHERE seller_id = $1", user["user_id"])
    return {"connected": False}


# ======================= Products =======================
def _clean_product_images(body: "ProductIn") -> List[str]:
    out: List[str] = []
    for p in (body.images or []):
        p = (p or "").strip()
        if p and security.is_safe_image_path(p) and p not in out:
            out.append(p)
    if not out and body.image and security.is_safe_image_path(body.image.strip()):
        out = [body.image.strip()]
    return out[:8]


def delivery_for(store: dict, subtotal: float) -> float:
    """The delivery charge this shop applies to an order of ``subtotal``.

    Free once the shop's free-delivery threshold is met; the threshold is
    inclusive, because "free delivery above ₹1,500" reads to a buyer as
    "spend ₹1,500 and it is free".
    """
    fee = float(store.get("delivery_fee") or 0)
    if fee <= 0:
        return 0.0
    threshold = store.get("free_delivery_above")
    if threshold is not None and subtotal >= float(threshold):
        return 0.0
    return round(fee, 2)


def _clean_payment_methods(body: "ProductIn") -> List[str]:
    """Keep the seller's selection in a stable order and never allow an empty
    set — a product with no payment method could not be bought."""
    chosen = {m.strip().lower() for m in (body.paymentMethods or [])}
    out = [m for m in PAYMENT_METHODS if m in chosen]
    return out or ["online"]


@api.post("/products")
async def create_product(body: ProductIn, user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=400, detail="Create a store first")

    images = _clean_product_images(body)
    primary = images[0] if images else None
    pay_methods = _clean_payment_methods(body)
    prod_id = new_id("prod")
    title = security.sanitize_text(body.title, 200)
    desc = security.sanitize_text(body.description, 2000)
    created_at = iso(now())
    option_groups_json = [og.model_dump() for og in body.optionGroups]
    prod_slug = await unique_product_slug(store["slug"], title)

    await db.execute(
        """
        INSERT INTO products (product_id, seller_id, store_slug, title, description, price, stock, option_groups, active, image, images, payment_methods, slug, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
        prod_id, user["user_id"], store["slug"], title, desc, body.price, body.stock,
        option_groups_json, body.active, primary, images, pay_methods, prod_slug, created_at
    )
    return {
        "product_id": prod_id, "sellerId": user["user_id"], "storeSlug": store["slug"],
        "title": title, "description": desc, "price": body.price, "stock": body.stock,
        "optionGroups": option_groups_json, "active": body.active,
        "image": primary, "images": images, "paymentMethods": pay_methods,
        "slug": prod_slug, "created_at": created_at,
    }


@api.get("/products")
async def my_products(user=Depends(get_current_user)):
    rows = await db.fetch_all("SELECT * FROM products WHERE seller_id = $1 ORDER BY created_at DESC LIMIT 500", user["user_id"])
    return [public_product(r) for r in rows]


@api.put("/products/{product_id}")
async def update_product(product_id: str, body: ProductIn, user=Depends(get_current_user)):
    prod = await db.fetch_one("SELECT * FROM products WHERE product_id = $1 AND seller_id = $2", product_id, user["user_id"])
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    images = _clean_product_images(body)
    primary = images[0] if images else None
    pay_methods = _clean_payment_methods(body)
    title = security.sanitize_text(body.title, 200)
    desc = security.sanitize_text(body.description, 2000)
    option_groups_json = [og.model_dump() for og in body.optionGroups]

    # Keep the existing slug unless the title changed — renaming a live product
    # shouldn't silently break the URL buyers already have.
    prod_slug = prod.get("slug")
    if not prod_slug or title != (prod.get("title") or ""):
        prod_slug = await unique_product_slug(prod["store_slug"], title, exclude_id=product_id)

    await db.execute(
        """
        UPDATE products
        SET title = $1, description = $2, price = $3, stock = $4, option_groups = $5, active = $6, image = $7, images = $8, payment_methods = $9, slug = $10
        WHERE product_id = $11 AND seller_id = $12
        """,
        title, desc, body.price, body.stock, option_groups_json, body.active, primary, images,
        pay_methods, prod_slug, product_id, user["user_id"]
    )
    updated = await db.fetch_one("SELECT * FROM products WHERE product_id = $1", product_id)
    return public_product(updated)


@api.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(get_current_user)):
    # Check ownership explicitly: db.execute() returns "SUCCESS" on SQLite and
    # "DELETE n" on Postgres, so there is no portable rowcount to test.
    owned = await db.fetch_one(
        "SELECT product_id FROM products WHERE product_id = $1 AND seller_id = $2",
        product_id, user["user_id"],
    )
    if not owned:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.execute("DELETE FROM products WHERE product_id = $1 AND seller_id = $2",
                     product_id, user["user_id"])
    return {"ok": True}


# ======================= Dashboard summary =======================
def _month_key(dt) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


@api.get("/dashboard/summary")
async def dashboard_summary(request: Request, user=Depends(get_current_user)):
    # Reads up to 2000 orders and aggregates them in Python, so it is the most
    # expensive authenticated call in the app.
    if not security.check_rate_limit(f"summary:{user['user_id']}", max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    """Every figure the dashboard shows, computed from this seller's own rows.

    One round trip instead of the client pulling orders and products and doing
    the arithmetic itself — which it cannot do correctly anyway, because
    /orders is paginated.
    """
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=400, detail="Create a store first")

    order_rows = await db.fetch_all(
        "SELECT * FROM orders WHERE seller_id = $1 ORDER BY created_at DESC LIMIT 2000",
        user["user_id"])
    product_rows = await db.fetch_all(
        "SELECT * FROM products WHERE seller_id = $1 ORDER BY created_at DESC LIMIT 500",
        user["user_id"])
    orders = [public_order(o) for o in order_rows]
    products = [public_product(p) for p in product_rows]

    sub_status = await effective_sub_status(user)
    is_pro = sub_status == "active"
    rate = COMMISSION_RATE_PRO if is_pro else COMMISSION_RATE_FREE

    now_dt = now()
    this_month, last_month = _month_key(now_dt), _month_key(
        (now_dt.replace(day=1) - timedelta(days=1)))

    # Money that has actually been earned: paid onwards, disputes excluded.
    EARNED = ("paid", "shipped", "delivered", "completed")

    def bucket(o):
        d = parse_dt(o.get("created_at"))
        return _month_key(d) if d else ""

    gross_this = sum(o["amount"] for o in orders if o["status"] in EARNED and bucket(o) == this_month)
    gross_last = sum(o["amount"] for o in orders if o["status"] in EARNED and bucket(o) == last_month)
    n_this = sum(1 for o in orders if bucket(o) == this_month)
    n_last = sum(1 for o in orders if bucket(o) == last_month)

    # Action queue — the things that need the seller today.
    to_ship = [o for o in orders if o["status"] == "paid"]
    awaiting_otp = [o for o in orders if o["status"] == "shipped"]
    disputed = [o for o in orders if o["status"] == "disputed"]
    low_stock = [p for p in products
                 if p["stock"] is not None and 0 < p["stock"] <= LOW_STOCK_THRESHOLD]
    out_of_stock = [p for p in products if p["stock"] == 0]

    # Where the money sits.
    held = sum(o["amount"] for o in orders
               if o["status"] in ("paid", "shipped") and o["paymentMethod"] != "cod")
    cash_collected = sum(o["amount"] for o in orders
                         if o["paymentMethod"] == "cod" and o["status"] in ("delivered", "completed"))
    settled = sum(o["amount"] for o in orders
                  if o["status"] == "completed" and o["paymentMethod"] != "cod")

    # Revenue per day, last 30 days, zero-filled so the chart has no gaps.
    days, day_index = [], {}
    for i in range(29, -1, -1):
        d = (now_dt - timedelta(days=i)).date().isoformat()
        day_index[d] = len(days)
        days.append({"date": d, "amount": 0.0, "orders": 0})
    for o in orders:
        dt = parse_dt(o.get("created_at"))
        if not dt or o["status"] not in EARNED:
            continue
        slot = day_index.get(dt.date().isoformat())
        if slot is not None:
            days[slot]["amount"] += o["amount"]
            days[slot]["orders"] += 1

    # Aggregates over earned orders.
    by_product, by_method, by_city, buyers = {}, {}, {}, {}
    for o in orders:
        if o["status"] not in EARNED:
            continue
        for it in (o.get("items") or []):
            key = it.get("productId") or it.get("title")
            e = by_product.setdefault(key, {"title": it.get("title") or "Product",
                                            "units": 0, "revenue": 0.0})
            qty = int(it.get("quantity") or 0)
            e["units"] += qty
            e["revenue"] += float(it.get("unitPrice") or 0) * qty
        by_method[o["paymentMethod"]] = by_method.get(o["paymentMethod"], 0) + 1
        city = ((o.get("address") or {}).get("city") or "").strip()
        if city:
            by_city[city] = by_city.get(city, 0) + 1
        em = (o.get("buyerEmail") or "").lower()
        if em:
            b = buyers.setdefault(em, {"orders": 0, "spend": 0.0, "name": o.get("buyerName") or "",
                                       "city": city, "lastAt": o.get("created_at")})
            b["orders"] += 1
            b["spend"] += o["amount"]

    top = lambda d, k: sorted(d, key=k, reverse=True)
    repeat = sum(1 for b in buyers.values() if b["orders"] > 1)

    route = await db.fetch_one("SELECT status FROM seller_routes WHERE seller_id = $1", user["user_id"])
    bank_ready = bool(route and route.get("status") in ("activated", "created", "mock"))

    return {
        "generatedAt": iso(now_dt),
        "queue": {
            "toShip": len(to_ship),
            "toShipValue": round(sum(o["amount"] for o in to_ship), 2),
            "oldestToShipAt": (to_ship[-1]["created_at"] if to_ship else None),
            "awaitingOtp": len(awaiting_otp),
            "disputed": len(disputed),
            "lowStock": len(low_stock),
            "outOfStock": len(out_of_stock),
            "lowStockTitles": [p["title"] for p in (low_stock + out_of_stock)[:4]],
            "bankReady": bank_ready,
        },
        "metrics": {
            "grossThisMonth": round(gross_this, 2),
            "grossLastMonth": round(gross_last, 2),
            "ordersThisMonth": n_this,
            "ordersLastMonth": n_last,
            "aov": round(gross_this / max(1, sum(1 for o in orders if o["status"] in EARNED and bucket(o) == this_month)), 2) if gross_this else 0,
            "commissionRate": rate,
            "netThisMonth": round(gross_this * (1 - rate), 2),
            "commissionThisMonth": round(gross_this * rate, 2),
            "isPro": is_pro,
            "totalOrders": len(orders),
            "repeatBuyers": repeat,
            "uniqueBuyers": len(buyers),
            "disputeRate": round(len(disputed) / len(orders) * 100, 1) if orders else 0.0,
        },
        "money": {
            "held": round(held, 2),
            "heldNet": round(held * (1 - rate), 2),
            "cashCollected": round(cash_collected, 2),
            "cashCommissionOwed": round(cash_collected * rate, 2),
            "settled": round(settled, 2),
            "disputedValue": round(sum(o["amount"] for o in disputed), 2),
        },
        "daily": days,
        "topProducts": [
            {"title": v["title"], "units": v["units"], "revenue": round(v["revenue"], 2)}
            for v in top(by_product.values(), lambda v: v["revenue"])[:5]
        ],
        "paymentMix": [{"method": k, "orders": v}
                       for k, v in top(by_method.items(), lambda kv: kv[1])[:5]],
        "topCities": [{"city": k, "orders": v}
                      for k, v in top(by_city.items(), lambda kv: kv[1])[:5]],
        "customers": [
            {"email": em, "name": b["name"], "city": b["city"], "orders": b["orders"],
             "spend": round(b["spend"], 2), "lastAt": b["lastAt"]}
            for em, b in top(buyers.items(), lambda kv: kv[1]["spend"])[:50]
        ],
        "counts": {
            "products": len(products),
            "liveProducts": sum(1 for p in products if p["active"]),
            "draftProducts": sum(1 for p in products if not p["active"]),
            "byStatus": {st: sum(1 for o in orders if o["status"] == st)
                         for st in ("placed", "paid", "shipped", "delivered", "completed", "disputed")},
        },
        "health": {
            "bankVerified": bank_ready,
            "hasBio": bool((store.get("bio") or "").strip()),
            "hasProducts": len(products) > 0,
            "hasProductImages": any(p["images"] for p in products),
            "codEnabled": any("cod" in p["paymentMethods"] for p in products),
            "hasGstin": bool((store.get("gstin") or "").strip()),
        },
    }


@api.post("/orders/bulk-ship")
async def bulk_ship(body: BulkOrderIn, user=Depends(get_current_user)):
    """Dispatch several orders at once. Each is shipped through the same path as
    the single-order route, so delivery OTPs still get generated and emailed."""
    done, failed = [], []
    for oid in body.orderIds:
        try:
            await ship_order(oid, user)
            done.append(oid)
        except HTTPException as exc:
            failed.append({"orderId": oid, "reason": exc.detail})
    return {"shipped": done, "failed": failed}



# ======================= AI copywriting =======================
def _own_upload_keys(user_id: str, paths: List[str]) -> List[str]:
    """Keep only images this seller uploaded themselves.

    storage.build_path writes to "<app>/uploads/<user_id>/<uuid>.<ext>", so the
    owner is in the key. Anything else — another seller's key, a remote URL — is
    dropped rather than fetched and billed for.
    """
    prefix = f"/uploads/{user_id}/"
    return [
        p for p in paths
        if p and security.is_safe_image_path(p) and prefix in p and not p.startswith(("http://", "https://"))
    ]


@api.get("/ai/status")
async def ai_status(user=Depends(get_current_user)):
    """Lets the product editor hide the button when no API key is configured."""
    return {"enabled": ai_service.enabled()}


@api.post("/ai/product-description")
async def ai_product_description(body: AIDescribeIn, request: Request,
                                 user=Depends(get_current_user)):
    """Stream a product description as Claude writes it (server-sent events)."""
    if not ai_service.enabled():
        raise HTTPException(status_code=503,
                            detail="AI descriptions aren't switched on for this site yet.")

    # Every call costs money and reads up to three images, so cap it per seller
    # rather than per IP — a shared office should not throttle everyone.
    if not security.check_rate_limit(f"ai_desc:{user['user_id']}", max_requests=40, window_seconds=3600):
        raise HTTPException(status_code=429,
                            detail="You've used this hour's AI drafts. Try again shortly.")

    store = await get_my_store(user)

    async def events():
        try:
            async for chunk in ai_service.stream_description(
                images=_own_upload_keys(user["user_id"], body.images),
                title=body.title,
                price=body.price,
                stock=body.stock,
                keywords=body.keywords,
                existing=body.description,
                option_groups=[g.model_dump() for g in body.optionGroups],
                store_name=(store or {}).get("name") or "",
                store_bio=(store or {}).get("bio") or "",
            ):
                yield f"data: {json.dumps({'type': 'delta', 'text': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except ai_service.AIUnavailable as exc:
            # Headers are already out by now, so the error has to travel as an
            # event rather than an HTTP status.
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ai description stream failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Something went wrong writing that. Try again.'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )



# ======================= AI shop assistant =======================
# The model can read this seller's shop and propose changes to it. It cannot
# write. Every tool below is closed over `user`, so there is no seller id in the
# model's reach — asking for "seller 42's products" is not a thing it can
# express. Applying a proposal is a separate, explicit request from the seller,
# and that route re-checks ownership and bounds rather than trusting what comes
# back.

# Wire name -> the tool's own argument name. An allowlist: a key that is not in
# here is dropped on apply, so a hand-written client cannot smuggle in a column.
_ASSISTANT_PRODUCT_KEYS = {
    "price": "price",
    "stock": "stock",
    "active": "active",
    "paymentMethods": "payment_methods",
}
_ASSISTANT_SETTINGS_KEYS = {
    "deliveryFee": "delivery_fee",
    "freeDeliveryAbove": "free_delivery_above",
    "dispatchDays": "dispatch_days",
}


def _assistant_tools(user: dict, request: Request):
    """Build the tool set bound to one authenticated seller."""
    seller_id = user["user_id"]

    async def _owned_product(product_id: str) -> dict:
        prod = await db.fetch_one(
            "SELECT * FROM products WHERE product_id = $1 AND seller_id = $2",
            str(product_id or ""), seller_id)
        if not prod:
            raise ai_assistant.ProposalError(
                "There's no product with that id in this shop. Use list_products to get the ids.")
        return public_product(prod)

    async def list_products(search: str = "", only_low_stock: bool = False,
                            only_drafts: bool = False) -> dict:
        rows = await db.fetch_all(
            "SELECT * FROM products WHERE seller_id = $1 ORDER BY created_at DESC LIMIT 500",
            seller_id)
        items = [public_product(r) for r in rows]
        needle = (search or "").strip().lower()
        if needle:
            items = [p for p in items if needle in (p["title"] or "").lower()]
        if only_low_stock:
            items = [p for p in items
                     if p["stock"] is not None and p["stock"] <= LOW_STOCK_THRESHOLD]
        if only_drafts:
            items = [p for p in items if not p["active"]]
        return {
            "count": len(items),
            "products": [
                {"product_id": p["product_id"], "title": p["title"], "price": p["price"],
                 "stock": p["stock"], "active": p["active"],
                 "paymentMethods": p["paymentMethods"], "hasImage": bool(p["images"])}
                for p in items[:60]
            ],
        }

    async def shop_overview() -> dict:
        # Reuses the dashboard's arithmetic so the assistant can never quote a
        # figure that disagrees with the screen the seller is looking at.
        s = await dashboard_summary(request, user)
        return {
            "queue": s["queue"], "metrics": s["metrics"], "money": s["money"],
            "topProducts": s["topProducts"], "paymentMix": s["paymentMix"],
            "topCities": s["topCities"], "counts": s["counts"], "health": s["health"],
        }

    async def list_orders(status: str = "", limit: int = 10) -> dict:
        rows = await db.fetch_all(
            "SELECT * FROM orders WHERE seller_id = $1 ORDER BY created_at DESC LIMIT 200",
            seller_id)
        orders = [public_order(o) for o in rows]
        if status:
            orders = [o for o in orders if o["status"] == status]
        try:
            cap = max(1, min(20, int(limit)))
        except (TypeError, ValueError):
            cap = 10
        return {
            "count": len(orders),
            "orders": [
                {
                    "order_id": o["order_id"],
                    "status": o["status"],
                    "amount": o["amount"],
                    "paymentMethod": o["paymentMethod"],
                    "placedAt": o["created_at"],
                    # Everything below was typed by a member of the public.
                    "buyerName": ai_assistant.fence_buyer_text(o["buyerName"]),
                    "city": ai_assistant.fence_buyer_text((o.get("address") or {}).get("city")),
                    "disputeReason": (ai_assistant.fence_buyer_text(o["disputeReason"])
                                      if o["disputeReason"] else None),
                    "items": [{"title": it.get("title"), "quantity": it.get("quantity")}
                              for it in (o.get("items") or [])][:10],
                }
                for o in orders[:cap]
            ],
        }

    async def get_settings() -> dict:
        store = await get_my_store(user)
        if not store:
            return {"error": "This seller hasn't created their shop yet."}
        return {
            "name": store["name"], "slug": store["slug"], "bio": store["bio"],
            "deliveryFee": store["deliveryFee"],
            "freeDeliveryAbove": store["freeDeliveryAbove"],
            "dispatchDays": store["dispatchDays"], "gstin": store["gstin"],
            "notifyNewOrder": store["notifyNewOrder"],
            "notifyDailySummary": store["notifyDailySummary"],
            "notifyWeeklyDigest": store["notifyWeeklyDigest"],
        }

    async def propose_product_update(product_id: str, reason: str, **patch) -> dict:
        prod = await _owned_product(product_id)
        changes = ai_assistant.validate_product_proposal(patch)
        before = {k: prod.get(k) for k in changes}
        if before == changes:
            raise ai_assistant.ProposalError(
                f"'{prod['title']}' is already set that way — nothing to change.")
        return {
            "queued": True,
            "note": "Shown to the seller. It only takes effect if they press Apply.",
            "proposal": {
                "kind": "product",
                "productId": prod["product_id"],
                "label": prod["title"],
                "reason": security.sanitize_text(str(reason or ""), 200),
                "before": before,
                "changes": changes,
            },
        }

    async def propose_settings_update(reason: str, **patch) -> dict:
        store = await get_my_store(user)
        if not store:
            raise ai_assistant.ProposalError("This seller hasn't created their shop yet.")
        changes = ai_assistant.validate_settings_proposal(patch)
        before = {k: store.get(k) for k in changes}
        if before == changes:
            raise ai_assistant.ProposalError("The shop is already set that way — nothing to change.")
        return {
            "queued": True,
            "note": "Shown to the seller. It only takes effect if they press Apply.",
            "proposal": {
                "kind": "settings",
                "productId": None,
                "label": "Shop settings",
                "reason": security.sanitize_text(str(reason or ""), 200),
                "before": before,
                "changes": changes,
            },
        }

    return {
        "list_products": list_products,
        "shop_overview": shop_overview,
        "list_orders": list_orders,
        "get_settings": get_settings,
        "propose_product_update": propose_product_update,
        "propose_settings_update": propose_settings_update,
    }


@api.post("/ai/assistant")
async def ai_assistant_chat(body: AssistantIn, request: Request,
                            user=Depends(get_current_user)):
    if not ai_service.enabled():
        raise HTTPException(status_code=503,
                            detail="The shop assistant isn't switched on for this site yet.")
    # A turn can fan out into several model calls, so it is the priciest thing a
    # seller can trigger. Per seller, not per IP.
    if not security.check_rate_limit(f"ai_chat:{user['user_id']}", max_requests=60, window_seconds=3600):
        raise HTTPException(status_code=429,
                            detail="You've used this hour's assistant messages. Try again shortly.")
    tools = _assistant_tools(user, request)
    history = [t.model_dump() for t in body.history]

    async def events():
        """Server-sent events, so the panel can say what it is doing.

        A turn is several model calls; on one HTTP response the seller stares
        at a spinner for all of them and reasonably concludes it has hung.
        """
        try:
            async for event in ai_assistant.run_stream(
                message=body.message, history=history, tools=tools):
                yield f"data: {json.dumps(event)}\n\n"
        except ai_assistant.AIUnavailable as exc:
            # Headers are already out, so the error travels as an event.
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("assistant turn failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'The assistant hit a problem. Try again.'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@api.post("/ai/assistant/apply")
async def ai_assistant_apply(body: AssistantApplyIn, user=Depends(get_current_user)):
    """Apply proposals the seller confirmed.

    This does not trust the body. The AI is not consulted, the product is looked
    up again under this seller's id, unknown keys are dropped and the same
    bounds run a second time. A proposal that has gone stale — the product was
    deleted meanwhile — fails on its own without stopping the rest.
    """
    if not security.check_rate_limit(f"ai_apply:{user['user_id']}", max_requests=120, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many changes at once. Try again shortly.")

    applied, failed = [], []
    for item in body.proposals:
        try:
            if item.kind == "product":
                prod = await db.fetch_one(
                    "SELECT * FROM products WHERE product_id = $1 AND seller_id = $2",
                    str(item.productId or ""), user["user_id"])
                if not prod:
                    raise ai_assistant.ProposalError("That product no longer exists.")
                current = public_product(prod)
                patch = {arg: item.changes[wire]
                         for wire, arg in _ASSISTANT_PRODUCT_KEYS.items() if wire in item.changes}
                changes = ai_assistant.validate_product_proposal(patch)

                columns = {"price": "price", "stock": "stock", "active": "active",
                           "paymentMethods": "payment_methods"}
                sets, values = [], []
                for key, value in changes.items():
                    if key == "paymentMethods":
                        value = [m for m in PAYMENT_METHODS if m in set(value)] or ["online"]
                    sets.append(f"{columns[key]} = ${len(values) + 1}")
                    values.append(value)
                values.extend([current["product_id"], user["user_id"]])
                await db.execute(
                    f"UPDATE products SET {', '.join(sets)} "
                    f"WHERE product_id = ${len(values) - 1} AND seller_id = ${len(values)}",
                    *values)
                applied.append({"kind": "product", "productId": current["product_id"],
                                "label": current["title"], "changes": changes})
            else:
                store = await get_my_store(user)
                if not store:
                    raise ai_assistant.ProposalError("No shop to change.")
                patch = {arg: item.changes[wire]
                         for wire, arg in _ASSISTANT_SETTINGS_KEYS.items() if wire in item.changes}
                changes = ai_assistant.validate_settings_proposal(patch)

                columns = {"deliveryFee": "delivery_fee",
                           "freeDeliveryAbove": "free_delivery_above",
                           "dispatchDays": "dispatch_days"}
                sets, values = [], []
                for key, value in changes.items():
                    sets.append(f"{columns[key]} = ${len(values) + 1}")
                    values.append(value)
                values.append(store["store_id"])
                await db.execute(
                    f"UPDATE stores SET {', '.join(sets)} WHERE store_id = ${len(values)}",
                    *values)
                applied.append({"kind": "settings", "productId": None,
                                "label": "Shop settings", "changes": changes})
        except ai_assistant.ProposalError as exc:
            failed.append({"kind": item.kind, "productId": item.productId, "reason": str(exc)})
        except (TypeError, ValueError) as exc:
            logger.warning("assistant apply rejected a proposal: %s", exc)
            failed.append({"kind": item.kind, "productId": item.productId,
                           "reason": "That change didn't look right, so nothing was saved."})

    return {"applied": applied, "failed": failed}


# ======================= Orders =======================
async def finalize_if_expired(order: dict) -> dict:
    """Auto-complete a delivered order once its acceptance window has elapsed
    with no dispute."""
    if order.get("status") == "delivered":
        exp = parse_dt(order.get("window_expires_at") or order.get("windowExpiresAt"))
        if exp and now() >= exp:
            await db.execute("UPDATE orders SET status = 'completed' WHERE order_id = $1 AND status = 'delivered'", order["order_id"])
            order["status"] = "completed"
    return order


async def _record_order(order_id, store, body: OrderIn, items, subtotal, created_at,
                        rp_order_id, rp_key_id, pay_method: str, delivery: float = 0.0,
                        amount: Optional[float] = None):
    await db.execute(
        """
        INSERT INTO orders (
            order_id, seller_id, store_slug, buyer_name, buyer_email, buyer_phone,
            address, items, subtotal, delivery_fee, tax, amount, status,
            razorpay_order_id, razorpay_key_id, payment_method, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'placed', $13, $14, $15, $16
        )
        """,
        order_id, store["seller_id"], store["slug"], body.buyerName, body.buyerEmail, body.buyerPhone,
        body.address, items, subtotal, delivery, 0,
        (subtotal + delivery) if amount is None else amount,
        rp_order_id, rp_key_id, pay_method, created_at
    )


async def _reserve_stock(demand: dict, prod_cache: dict):
    """Decrement stock, guarded so it can never go negative under a race."""
    for pid, d in demand.items():
        if prod_cache[pid].get("stock") is not None:
            await db.execute(
                "UPDATE products SET stock = stock - $1 WHERE product_id = $2 AND stock >= $3",
                d["product_qty"], pid, d["product_qty"]
            )


async def _notify_new_order(store, order_id, total, items, body: OrderIn):
    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", store["seller_id"])
    if not seller:
        return
    order_doc = {
        "order_id": order_id, "amount": total, "items": items,
        "buyerName": body.buyerName, "buyerEmail": body.buyerEmail,
    }
    asyncio.create_task(email_service.send_new_order_email(
        seller["email"], seller.get("name"), order_doc, f"{FRONTEND_URL}/orders/{order_id}"))


@api.post("/shop/{slug}/checkout")
async def checkout(slug: str, body: OrderIn, request: Request):
    client_ip = get_client_ip(request)
    if not security.check_rate_limit(f"order:{client_ip}", max_requests=30, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many orders placed. Please try again in a few minutes.")

    store = await db.fetch_one("SELECT * FROM stores WHERE slug = $1", slug.lower().strip())
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    items = []
    total = 0.0
    prod_cache = {}
    demand = {}
    for it in body.items:
        if it.quantity < 1 or it.quantity > 1000:
            raise HTTPException(status_code=400, detail="Invalid item quantity")
        prod = prod_cache.get(it.productId)
        if prod is None:
            raw_prod = await db.fetch_one("SELECT * FROM products WHERE product_id = $1 AND active = TRUE", it.productId)
            if not raw_prod or raw_prod["store_slug"] != store["slug"]:
                raise HTTPException(status_code=400, detail=f"Invalid product {it.productId}")
            prod = public_product(raw_prod)
            prod_cache[it.productId] = prod
        unit = float(prod["price"])
        d = demand.setdefault(it.productId, {"product_qty": 0, "options": {}})
        d["product_qty"] += it.quantity
        for g in prod.get("optionGroups", []):
            gname = g["name"]
            if gname not in it.optionSelections:
                raise HTTPException(status_code=400, detail=f"Select an option for {gname}")
            chosen = next((o for o in g["options"] if o["label"] == it.optionSelections[gname]), None)
            if not chosen:
                raise HTTPException(status_code=400, detail=f"Invalid option for {gname}")
            unit += float(chosen.get("priceDelta") or 0)
            d["options"].setdefault(gname, {})
            d["options"][gname][chosen["label"]] = d["options"][gname].get(chosen["label"], 0) + it.quantity
        if unit < 0:
            raise HTTPException(status_code=400, detail="Invalid calculated unit price")
        line_total = unit * it.quantity
        total += line_total
        items.append({"productId": it.productId, "title": prod["title"],
                      "optionSelections": it.optionSelections, "quantity": it.quantity,
                      "unitPrice": unit})

    # Stock check (product-level).
    for pid, d in demand.items():
        prod = prod_cache[pid]
        stock = prod.get("stock")
        if stock is not None and d["product_qty"] > stock:
            raise HTTPException(status_code=409, detail=f"Only {stock} left of “{prod['title']}”.")

    # Payment method must be offered by every product in the cart.
    pay_method = (body.paymentMethod or "online").strip().lower()
    if pay_method not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Unsupported payment method")
    allowed = set(PAYMENT_METHODS)
    for prod in prod_cache.values():
        allowed &= set(prod.get("paymentMethods") or ["online"])
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail="These items don't share a payment method. Please order them separately.",
        )
    if pay_method not in allowed:
        label = "Cash on delivery" if pay_method == "cod" else "Online payment"
        raise HTTPException(status_code=400, detail=f"{label} isn't available for every item in this order.")

    order_id = new_id("ord")
    created_at = iso(now())

    subtotal = total
    delivery = delivery_for(store, subtotal)
    total = round(subtotal + delivery, 2)

    amount_paise = int(round(total * 100))
    if amount_paise <= 0:
        raise HTTPException(status_code=400, detail="Order total must be greater than zero")

    route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", store["seller_id"])
    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", store["seller_id"])
    seller_sub = await effective_sub_status(seller) if seller else "inactive"
    commission_pct = COMMISSION_RATE_PRO if seller_sub == "active" else COMMISSION_RATE_FREE

    rp_order_id = None
    rp_key_id = None

    if pay_method == "cod":
        # No gateway leg — the seller collects cash at handover.
        await _record_order(order_id, store, body, items, subtotal, created_at, None, None, "cod",
                            delivery=delivery, amount=total)
        await _reserve_stock(demand, prod_cache)
        await _notify_new_order(store, order_id, total, items, body)
        return {"orderId": order_id, "amount": total, "subtotal": subtotal,
                "deliveryFee": delivery, "paymentMethod": "cod",
                "razorpayOrderId": None, "razorpayKeyId": None}

    rc, plat_kid, _ = route_service.platform_client()
    if not rc:
        raise HTTPException(status_code=503, detail="Online payments are unavailable right now. Please try again shortly.")

    seller_payout_paise = int(round(amount_paise * (1.0 - commission_pct)))

    order_payload = {
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
        "receipt": order_id[:40],
        "notes": {"platform": "Stall Wise", "storeSlug": store["slug"], "orderId": order_id},
    }
    routed = bool(route and route.get("mode") == "razorpay" and route.get("account_id"))
    if routed:
        order_payload["transfers"] = [{
            "account": route["account_id"],
            "amount": seller_payout_paise,
            "currency": "INR",
            "on_hold": 0,
            "notes": {
                "platform": "Stall Wise",
                "storeSlug": store["slug"],
                "commission": f"{int(commission_pct * 100)}%",
            },
        }]

    try:
        rp = await asyncio.to_thread(rc.order.create, order_payload)
    except Exception as e:
        if routed:
            logger.warning(f"Razorpay routed order create failed ({e}); retrying without transfer")
            order_payload.pop("transfers", None)
            try:
                rp = await asyncio.to_thread(rc.order.create, order_payload)
            except Exception as e2:
                logger.error(f"Razorpay order creation failed: {e2}")
                raise HTTPException(status_code=502, detail="Could not start the payment. Please try again.")
        else:
            logger.error(f"Razorpay order creation failed: {e}")
            raise HTTPException(status_code=502, detail="Could not start the payment. Please try again.")

    rp_order_id = rp["id"]
    rp_key_id = plat_kid

    await _record_order(order_id, store, body, items, subtotal, created_at, rp_order_id, rp_key_id,
                        "online", delivery=delivery, amount=total)
    await _reserve_stock(demand, prod_cache)
    await _notify_new_order(store, order_id, total, items, body)

    return {
        "orderId": order_id,
        "subtotal": subtotal,
        "deliveryFee": delivery,
        "amount": total,
        "paymentMethod": "online",
        "razorpayOrderId": rp_order_id,
        "razorpayKeyId": rp_key_id,
    }


@api.post("/orders")
async def create_order_alias(body: OrderIn, request: Request):
    return await checkout(body.storeSlug, body, request)


@api.get("/orders")
async def list_orders(status: Optional[str] = Query(None),
                      page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100),
                      user=Depends(get_current_user)):
    skip = (page - 1) * limit
    if status:
        total = await db.fetch_val("SELECT COUNT(*) FROM orders WHERE seller_id = $1 AND status = $2", user["user_id"], status)
        rows = await db.fetch_all("SELECT * FROM orders WHERE seller_id = $1 AND status = $2 ORDER BY created_at DESC LIMIT $3 OFFSET $4", user["user_id"], status, limit, skip)
    else:
        total = await db.fetch_val("SELECT COUNT(*) FROM orders WHERE seller_id = $1", user["user_id"])
        rows = await db.fetch_all("SELECT * FROM orders WHERE seller_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3", user["user_id"], limit, skip)

    rows = [await finalize_if_expired(r) for r in rows]
    orders = [public_order(r) for r in rows]
    return {"orders": orders, "total": total or 0, "page": page, "limit": limit,
            "pages": max(1, ((total or 0) + limit - 1) // limit)}


@api.get("/orders/{order_id}")
async def seller_order_detail(order_id: str, user=Depends(get_current_user)):
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1 AND seller_id = $2", order_id, user["user_id"])
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o = await finalize_if_expired(o)
    return public_order(o)


@api.get("/order/{order_id}")
async def buyer_order_detail(order_id: str, request: Request, email: str = Query("")):
    # This response carries the buyer's name, phone, address and delivery code.
    # Without a limit an order id could be paired against guessed emails freely.
    if not security.check_rate_limit(f"order_view:{get_client_ip(request)}", max_requests=60, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    # Require the buyer's email — the response carries PII and the delivery OTP.
    if not o or (o.get("buyer_email") or "").lower() != email.lower().strip():
        raise HTTPException(status_code=404, detail="Order not found")
    o = await finalize_if_expired(o)
    return public_order(o, for_buyer=True)


def _order_pay_secret() -> str:
    _, _, ksec = route_service.platform_client()
    return ksec or ""


@api.post("/orders/{order_id}/verify-payment")
async def verify_order_payment(order_id: str, body: PayVerifyIn):
    """Called by the buyer's browser right after Razorpay checkout succeeds.
    Verifies the payment signature before marking the order paid."""
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] != "placed":
        return public_order(o, for_buyer=True)
    if o.get("razorpay_order_id") and o["razorpay_order_id"] != body.razorpay_order_id:
        raise HTTPException(status_code=400, detail="This payment does not match the order")

    ksec = _order_pay_secret()
    if not ksec:
        raise HTTPException(status_code=503, detail="Payments are not configured")
    msg = f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode("utf-8")
    expected = hmac.new(ksec.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    await db.execute(
        "UPDATE orders SET status = 'paid', paid_at = $1, razorpay_payment_id = $2 WHERE order_id = $3 AND status = 'placed'",
        iso(now()), body.razorpay_payment_id, order_id
    )
    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", o["seller_id"])
    if seller:
        asyncio.create_task(email_service.send_payment_email(
            seller["email"], seller.get("name"), order_id, float(o.get("amount", 0)),
            f"{FRONTEND_URL}/orders/{order_id}"))
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    return public_order(o, for_buyer=True)


@api.post("/order/{order_id}/dispute")
async def raise_dispute(order_id: str, body: DisputeIn, request: Request):
    if not security.check_rate_limit(f"dispute:{get_client_ip(request)}", max_requests=20, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if (o.get("buyer_email") or "").lower() != body.email.lower().strip():
        raise HTTPException(status_code=403, detail="That email does not match this order")
    o = await finalize_if_expired(o)
    if o["status"] == "disputed":
        return {"status": "disputed"}
    if o["status"] != "delivered":
        raise HTTPException(status_code=400, detail="A dispute can only be raised on a delivered order")
    exp = parse_dt(o.get("window_expires_at"))
    if exp and now() > exp:
        raise HTTPException(status_code=400, detail="The acceptance window has already closed")

    reason = security.sanitize_text(body.reason, 1000)
    await db.execute("UPDATE orders SET status = 'disputed', dispute_reason = $1 WHERE order_id = $2", reason, order_id)
    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", o["seller_id"])
    if seller:
        asyncio.create_task(email_service.send_dispute_email(
            seller["email"], seller.get("name"), order_id, reason,
            f"{FRONTEND_URL}/orders/{order_id}"))
    return {"status": "disputed"}


@api.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
    if secret:
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        logger.warning("RAZORPAY_WEBHOOK_SECRET is not set — webhook processed without signature verification")

    try:
        data = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = data.get("event")
    payment = data.get("payload", {}).get("payment", {}).get("entity", {})
    rp_order_id = payment.get("order_id") or data.get("payload", {}).get("order", {}).get("entity", {}).get("id")
    rp_payment_id = payment.get("id")

    if rp_order_id and event in ("payment.captured", "order.paid"):
        await db.execute(
            "UPDATE orders SET status = 'paid', paid_at = $1, razorpay_payment_id = COALESCE($2, razorpay_payment_id) WHERE razorpay_order_id = $3 AND status = 'placed'",
            iso(now()), rp_payment_id, rp_order_id
        )
    return {"status": "ok"}


@api.post("/orders/{order_id}/ship")
async def ship_order(order_id: str, user=Depends(get_current_user)):
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1 AND seller_id = $2", order_id, user["user_id"])
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    is_cod = (o.get("payment_method") or "online") == "cod"
    # Cash-on-delivery orders ship before any money changes hands.
    if o["status"] != "paid" and not (is_cod and o["status"] == "placed"):
        raise HTTPException(status_code=400, detail="Order must be paid before shipping")

    otp = security.generate_otp()
    otp_hash = security.hash_otp(otp)
    otp_enc = security.encrypt_secret(otp)
    shipped_at = iso(now())

    await db.execute(
        """
        UPDATE orders
        SET status = 'shipped', otp_code_hash = $1, otp_enc = $2, otp_generated_at = $3,
            otp_attempts = 0, otp_locked = FALSE, shipped_at = $4
        WHERE order_id = $5
        """,
        otp_hash, otp_enc, shipped_at, shipped_at, order_id
    )
    asyncio.create_task(email_service.send_otp_email(o["buyer_email"], o["buyer_name"], otp, f"{FRONTEND_URL}/order/{order_id}"))
    return {"status": "shipped"}


@api.post("/orders/{order_id}/confirm-delivery")
async def confirm_delivery(order_id: str, body: OtpIn, request: Request, user=Depends(get_current_user)):
    client_ip = get_client_ip(request)
    if not security.check_rate_limit(f"otp_conf:{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait a moment.")

    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1 AND seller_id = $2", order_id, user["user_id"])
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] != "shipped":
        raise HTTPException(status_code=400, detail="Order not ready for delivery confirmation")
    if o.get("otp_locked"):
        raise HTTPException(status_code=423, detail="OTP locked after too many failed attempts")

    if not security.verify_otp(body.otp.strip(), o.get("otp_code_hash", "")):
        attempts = (o.get("otp_attempts") or 0) + 1
        locked = attempts >= OTP_MAX_ATTEMPTS
        await db.execute("UPDATE orders SET otp_attempts = $1, otp_locked = $2 WHERE order_id = $3", attempts, locked, order_id)
        if locked:
            raise HTTPException(status_code=423, detail="Too many failed attempts. Code locked.")
        raise HTTPException(status_code=400, detail=f"Invalid OTP code ({attempts}/{OTP_MAX_ATTEMPTS} attempts)")

    store = await db.fetch_one("SELECT acceptance_window_minutes FROM stores WHERE slug = $1", o["store_slug"])
    window_min = int((store or {}).get("acceptance_window_minutes") or DEFAULT_WINDOW_MIN)
    delivered_at = iso(now())
    window_expires_at = iso(now() + timedelta(minutes=window_min))
    # A COD order is settled the moment the seller takes the cash at handover.
    paid_at = o.get("paid_at") or (delivered_at if (o.get("payment_method") or "online") == "cod" else None)
    await db.execute(
        "UPDATE orders SET status = 'delivered', delivered_at = $1, window_expires_at = $2, paid_at = $3 WHERE order_id = $4",
        delivered_at, window_expires_at, paid_at, order_id
    )
    return {"status": "delivered", "windowExpiresAt": window_expires_at}


# ======================= Subscription / Billing =======================
PRO_MONTHLY_AMOUNT = 199
PRO_YEARLY_AMOUNT = 1499
SUB_CURRENCY = "INR"
_PLAN_SPECS = {
    "monthly": {"period": "monthly", "interval": 1, "amount": PRO_MONTHLY_AMOUNT},
    "yearly": {"period": "yearly", "interval": 1, "amount": PRO_YEARLY_AMOUNT},
}

# Razorpay platform keys — from the environment only.
_RP_KEY_ID = (os.environ.get("RAZORPAY_KEY_ID") or "").strip()
_RP_KEY_SECRET = (os.environ.get("RAZORPAY_KEY_SECRET") or "").strip()


def platform_rp_client():
    if not _RP_KEY_ID or not _RP_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Platform billing is not configured yet")
    return route_service.razorpay_client(_RP_KEY_ID, _RP_KEY_SECRET), _RP_KEY_ID


@api.get("/subscription")
async def get_subscription(user=Depends(get_current_user)):
    status = await effective_sub_status(user)
    kid = _RP_KEY_ID
    return {
        "subscriptionStatus": status,
        "premiumTier": PREMIUM_TIER,
        "freeTier": FREE_TIER,
        "commissionRate": 0.00 if status == "active" else 0.10,
        "plans": {"monthly": PRO_MONTHLY_AMOUNT, "yearly": PRO_YEARLY_AMOUNT},
        "currency": SUB_CURRENCY,
        "billingConfigured": bool(kid),
        "subscriptionId": user.get("subscription_id") or user.get("subscriptionId"),
        "subscriptionInterval": user.get("subscription_interval") or user.get("subscriptionInterval"),
        "subscriptionExpiresAt": user.get("subscription_expires_at") or user.get("subscriptionExpiresAt"),
    }


@api.post("/subscription/create")
async def create_subscription(body: SubCreateIn, user=Depends(get_current_user)):
    interval = body.interval.lower().strip()
    if interval not in _PLAN_SPECS:
        raise HTTPException(status_code=400, detail="Invalid interval. Must be 'monthly' or 'yearly'")
    
    plan = _PLAN_SPECS[interval]
    amount = plan["amount"]
    
    kid = _RP_KEY_ID
    ksec = _RP_KEY_SECRET
    
    if not kid or not ksec:
        raise HTTPException(status_code=503, detail="Platform Razorpay credentials not configured")

    # Live Real Money Razorpay Order Creation
    try:
        rp_client = route_service.razorpay_client(kid, ksec)
        amount_paise = int(round(amount * 100))
        rp_order = await asyncio.to_thread(rp_client.order.create, {
            "amount": amount_paise,
            "currency": SUB_CURRENCY,
            "payment_capture": 1,
            "notes": {
                "type": "platform_subscription",
                "userId": user["user_id"],
                "interval": interval,
                "tier": PREMIUM_TIER,
            },
        })
        return {
            "mode": "order",
            "orderId": rp_order["id"],
            "amount": amount,
            "currency": SUB_CURRENCY,
            "keyId": kid,
            "tier": PREMIUM_TIER,
        }
    except razorpay.errors.BadRequestError as e:
        # Razorpay says "Authentication failed" when the key/secret pair is
        # rejected — rotated, mismatched (a live id with a test secret) or from
        # an account that is not activated for live mode. It is a platform
        # misconfiguration, not something the seller did, and the same keys back
        # every buyer checkout: if this fires, online payments are down shopwide.
        if "authentication" in str(e).lower():
            logger.critical(
                "RAZORPAY CREDENTIALS REJECTED — RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are "
                "not accepted by Razorpay. Every online payment is failing, not just "
                "subscriptions. Check the pair in the deployment environment."
            )
            raise HTTPException(
                status_code=503,
                detail="Payments are temporarily unavailable. We have been notified.",
            )
        logger.error(f"Razorpay rejected the subscription order: {e}")
        raise HTTPException(status_code=502, detail="Could not start the payment. Please try again.")
    except Exception as e:
        logger.error(f"Live Razorpay subscription order creation failed: {e}", exc_info=True)
        # Never hand the raw gateway message to the client.
        raise HTTPException(status_code=502, detail="Could not start the payment. Please try again.")


@api.post("/subscription/verify-payment")
async def verify_subscription_payment(body: PayVerifyIn, user=Depends(get_current_user)):
    kid = _RP_KEY_ID
    ksec = _RP_KEY_SECRET
    if not kid or not ksec:
        raise HTTPException(status_code=503, detail="Platform billing credentials not configured")
    
    # Verify HMAC signature
    msg = f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(ksec.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed")
    
    # Fetch Razorpay order details to know interval
    rp_client = route_service.razorpay_client(_RP_KEY_ID, _RP_KEY_SECRET)
    rp_order = await asyncio.to_thread(rp_client.order.fetch, body.razorpay_order_id)
    notes = rp_order.get("notes") or {}
    interval = notes.get("interval", "monthly")
    
    days = 365 if interval == "yearly" else 30
    expires_at = iso(now() + timedelta(days=days))
    
    await db.execute(
        """
        UPDATE users
        SET subscription_status = 'active',
            subscription_id = $1,
            subscription_interval = $2,
            subscription_expires_at = $3
        WHERE user_id = $4
        """,
        body.razorpay_payment_id, interval, expires_at, user["user_id"]
    )
    
    return {
        "ok": True,
        "subscriptionStatus": "active",
        "subscriptionInterval": interval,
        "subscriptionExpiresAt": expires_at,
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Reports config problems that don't stop the app but do lose data or
    disable features — visible without shell access to the container."""
    out = {
        "status": "ok",
        "service": "stallwise",
        "db": bool(db._pool),
        "engine": "postgres" if db._pool else "sqlite",
    }
    warning = db.ephemeral_storage_warning()
    if warning:
        out["status"] = "degraded"
        out["warning"] = warning
    missing = [k for k in ("ENCRYPTION_KEY", "JWT_SECRET", "RAZORPAY_KEY_ID",
                           "RAZORPAY_KEY_SECRET", "BREVO_API_KEY")
               if not (os.environ.get(k) or "").strip()]
    if missing:
        out["status"] = "degraded"
        out["missingConfig"] = missing
    # The AI features are optional, so a missing key is not "degraded" — but it
    # is the only way to tell from Railway whether the key actually landed.
    out["ai"] = {"enabled": ai_service.enabled(),
                 "model": ai_service.MODEL,
                 "assistantModel": ai_assistant.MODEL}
    # DEV_OTP_ECHO returns login OTPs in API responses. On a public deployment
    # that is a complete authentication bypass, so say so loudly.
    if (os.environ.get("DEV_OTP_ECHO") or "").lower() == "true":
        out["status"] = "insecure"
        out["danger"] = "DEV_OTP_ECHO is enabled — login OTPs are being returned in API responses. Unset it."
    return out


@api.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"service": "Stall Wise API", "status": "ok", "engine": "PostgreSQL", "db_connected": bool(db._pool)}


app.include_router(api)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Production static assets mounting for single-service Railway deployment
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    _DIST_REAL = os.path.realpath(DIST_DIR)
    _index_cache: Dict[str, Any] = {"mtime": None, "html": ""}

    def _base_index() -> str:
        """dist/index.html, re-read whenever the build changes."""
        path = os.path.join(_DIST_REAL, "index.html")
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return ""
        if _index_cache["mtime"] != mtime:
            with open(path, "r", encoding="utf-8") as f:
                _index_cache["html"] = f.read()
            _index_cache["mtime"] = mtime
        return _index_cache["html"]

    async def _seo_meta_for(route: str) -> dict:
        """Resolve the SEO tags for a route: /{store} renders that shop, and
        /{store}/{product} renders the product with its own Product schema."""
        r = (route or "").strip("/")
        if not r or seo.is_noindex(r):
            return seo.static_meta(r)

        parts = r.split("/")
        if len(parts) <= 2 and parts[0] not in seo.STATIC_PAGES:
            store = await db.fetch_one("SELECT * FROM stores WHERE slug = $1", parts[0].lower())
            if not store:
                # A shop that does not exist. The SPA still renders (the router
                # shows its own not-found state), but this must never be offered
                # to a search engine: without noindex, every scanner probe and
                # mistyped link becomes an indexable duplicate of the homepage.
                return {**seo.static_meta(""), "canonical": f"{seo.SITE_URL}/{r}", "noindex": True}
            if store:
                seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", store["seller_id"]) or {}
                if len(parts) == 2:
                    prod = await db.fetch_one(
                        "SELECT * FROM products WHERE store_slug = $1 AND slug = $2 AND active = TRUE",
                        store["slug"], parts[1].lower(),
                    )
                    if prod:
                        return seo.product_meta(store, seller, public_product(prod))
                    return {**seo.static_meta(""), "canonical": f"{seo.SITE_URL}/{store['slug']}", "noindex": True}
                rows = await db.fetch_all(
                    "SELECT * FROM products WHERE store_slug = $1 AND active = TRUE ORDER BY created_at DESC LIMIT 50",
                    store["slug"],
                )
                return seo.store_meta(store, seller, [public_product(p) for p in rows])

        if parts[0] == "shops" and len(parts) == 1:
            count = await db.fetch_val("SELECT COUNT(*) FROM stores") or 0
            return seo.directory_meta(count)

        return seo.static_meta(r)

    @app.get("/robots.txt", include_in_schema=False)
    async def robots_txt():
        return Response(content=seo.robots_txt(), media_type="text/plain")

    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap_xml():
        stores, products = [], []
        try:
            stores = await db.fetch_all(
                "SELECT slug, created_at FROM stores ORDER BY created_at DESC LIMIT 5000"
            )
            products = await db.fetch_all(
                """
                SELECT store_slug, slug, created_at FROM products
                WHERE active = TRUE AND slug IS NOT NULL
                ORDER BY created_at DESC LIMIT 40000
                """
            )
        except Exception as e:
            logger.error(f"sitemap lookup failed: {e}")
        return Response(content=seo.sitemap_xml(stores, products), media_type="application/xml")

    def _is_spa_route(rel: str) -> bool:
        """Could this path plausibly be a page in the app?

        Every unmatched path used to fall through to index.html with a 200, so
        scanners probing /.env, /.git/config, /wp-login.php and the like all got
        "200 OK". Nothing sensitive was served — the response was always the SPA
        shell — but Google will happily index a soft 404, and a log where every
        request is 200 hides real failures.

        App routes are slugs: no dot in the last segment, no dot-directories.
        Real files under dist/ are matched before this is consulted.
        """
        if not rel:
            return True
        segments = rel.split("/")
        if any(seg.startswith(".") for seg in segments):
            return False           # .env, .git/config, .ssh/id_rsa
        if "." in segments[-1]:
            return False           # wp-login.php, dump.sql, backup.tar.gz
        return True

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("uploads"):
            raise HTTPException(status_code=404, detail="Not found")
        rel = (full_path or "").lstrip("/\\")
        candidate = os.path.realpath(os.path.join(_DIST_REAL, rel))
        if (
            rel
            and (candidate == _DIST_REAL or candidate.startswith(_DIST_REAL + os.sep))
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)

        if not _is_spa_route(rel):
            raise HTTPException(status_code=404, detail="Not found")

        base = _base_index()
        if not base:
            raise HTTPException(status_code=404, detail="Not found")
        try:
            meta = await _seo_meta_for(rel)
            head = seo.build_head(
                title=meta["title"],
                description=meta["description"],
                canonical=meta["canonical"],
                image=meta.get("image"),
                noindex=meta.get("noindex", False),
                og_type=meta.get("og_type", "website"),
                jsonld=meta.get("jsonld"),
            )
            body = seo.inject(base, head)
        except Exception as e:
            logger.error(f"SEO render failed for /{rel}: {e}")
            body = base
        return Response(content=body, media_type="text/html; charset=utf-8")

# Explicit, credentialed CORS allowlist. Add deploy/preview origins via
# EXTRA_CORS_ORIGINS (comma-separated) rather than matching whole providers —
# `*.vercel.app` with credentials would let any Vercel site call this API.
cors_origins = {FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"}
for o in (os.environ.get("EXTRA_CORS_ORIGINS") or "").split(","):
    o = o.strip().rstrip("/")
    if o:
        cors_origins.add(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(cors_origins),
    allow_origin_regex=r"http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ======================= Startup =======================
async def backfill_product_slugs():
    """Give pre-existing products a URL slug so /{store}/{product} resolves."""
    rows = await db.fetch_all(
        "SELECT product_id, store_slug, title FROM products WHERE slug IS NULL OR slug = '' LIMIT 5000"
    )
    for r in rows:
        slug = await unique_product_slug(r["store_slug"], r["title"], exclude_id=r["product_id"])
        await db.execute("UPDATE products SET slug = $1 WHERE product_id = $2", slug, r["product_id"])
    if rows:
        logger.info(f"Backfilled slugs for {len(rows)} product(s)")


@app.on_event("startup")
async def on_startup():
    try:
        await db.init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}. Check that DATABASE_URL is set in your Railway variables!")
    try:
        await asyncio.to_thread(storage.init_storage)
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"storage init failed: {e}")
    try:
        await backfill_product_slugs()
    except Exception as e:
        logger.error(f"product slug backfill failed: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    await db.close_db()
