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
from typing import List, Optional, Dict

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

import httpx
import razorpay
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, Query, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

import db
import security
import email_service
import storage
import route_service

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
PREMIUM_TIER = "Stall Wise Pro"
FREE_TIER = "Community"
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


class GoogleSessionIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=256)


class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=2, max_length=60)
    bio: str = Field(default="", max_length=500)
    acceptanceWindowMinutes: int = Field(default=DEFAULT_WINDOW_MIN, ge=1, le=10080)


class StoreUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    acceptanceWindowMinutes: Optional[int] = Field(default=None, ge=1, le=10080)


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


class OtpIn(BaseModel):
    otp: str = Field(min_length=4, max_length=10)


class VerifyOtpIn(BaseModel):
    otp_id: str
    otp: str = Field(min_length=6, max_length=6)


class ResendOtpIn(BaseModel):
    otp_id: str


class SubSimIn(BaseModel):
    status: str  # active | inactive


class SubCreateIn(BaseModel):
    interval: str  # monthly | yearly


class PayVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ======================= Auth helpers =======================
_IS_DEV = FRONTEND_URL.startswith("http://localhost") or FRONTEND_URL.startswith("http://127.0.0.1")
_COOKIE_SECURE = not _IS_DEV
_COOKIE_SAMESITE = "lax" if _IS_DEV else "none"


def set_jwt_cookies(resp: Response, user_id: str, email: str):
    # 6-month (180 days) access token, 1-year (365 days) refresh token
    resp.set_cookie("access_token", security.create_access_token(user_id, email),
                    httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE, max_age=15552000, path="/")
    resp.set_cookie("refresh_token", security.create_refresh_token(user_id),
                    httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE, max_age=31536000, path="/")


def public_user(u: Optional[dict]) -> Optional[dict]:
    if not u:
        return None
    return {
        "user_id": u["user_id"],
        "email": u["email"],
        "name": u.get("name"),
        "role": u.get("role", "seller"),
        "authProvider": u.get("auth_provider") or u.get("authProvider", "password"),
        "subscriptionStatus": u.get("subscription_status") or u.get("subscriptionStatus", "inactive"),
        "picture": u.get("picture"),
        "avatar": u.get("avatar"),
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
        "image": p.get("image"),
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
        "razorpayOrderId": o.get("razorpay_order_id") or o.get("razorpayOrderId"),
        "razorpayPaymentId": o.get("razorpay_payment_id") or o.get("razorpayPaymentId"),
        "razorpayKeyId": o.get("razorpay_key_id") or o.get("razorpayKeyId"),
        "mockPayment": bool(o.get("mock_payment") or o.get("mockPayment", False)),
        "otpAttempts": o.get("otp_attempts") or o.get("otpAttempts", 0),
        "otpLocked": bool(o.get("otp_locked") or o.get("otpLocked", False)),
        "otpGeneratedAt": o.get("otp_generated_at") or o.get("otpGeneratedAt"),
        "shippedAt": o.get("shipped_at") or o.get("shippedAt"),
        "paidAt": o.get("paid_at") or o.get("paidAt"),
        "deliveredAt": o.get("delivered_at") or o.get("deliveredAt"),
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
async def _create_auth_otp(user_id: str, email: str, name: str, purpose: str) -> dict:
    otp = security.generate_otp()
    otp_id = new_id("otp")
    created_at = iso(now())
    expires_at = iso(now() + timedelta(minutes=AUTH_OTP_EXPIRY_MIN))
    otp_hash = security.hash_otp(otp)

    await db.execute(
        """
        INSERT INTO pending_otps (otp_id, user_id, email, otp_hash, purpose, attempts, locked, created_at, expires_at)
        VALUES ($1, $2, $3, $4, $5, 0, FALSE, $6, $7)
        """,
        otp_id, user_id, email, otp_hash, purpose, created_at, expires_at
    )
    # Send email in background asynchronously
    asyncio.create_task(email_service.send_auth_otp_email(email, name, otp))
    logger.info(f"Auth OTP for {email} ({purpose}): {otp}")
    return {"otp_id": otp_id}


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
        created_at = iso(now())

        await db.execute(
            """
            INSERT INTO users (user_id, email, name, password_hash, role, auth_provider, subscription_status, created_at)
            VALUES ($1, $2, $3, $4, 'seller', 'password', 'inactive', $5)
            """,
            user_id, email, clean_name, password_hash, created_at
        )
        otp_info = await _create_auth_otp(user_id, email, clean_name, "register")
        return {"pendingOtp": True, "email": email, "otpId": otp_info["otp_id"]}
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
        return {"pendingOtp": True, "email": email, "otpId": otp_info["otp_id"]}
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
    
    user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", rec["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute("DELETE FROM pending_otps WHERE otp_id = $1", body.otp_id)
    set_jwt_cookies(response, user["user_id"], user["email"])
    return public_user(user)


@api.post("/auth/resend-otp")
async def resend_auth_otp(body: ResendOtpIn, request: Request):
    client_ip = get_client_ip(request)
    if not security.check_rate_limit(f"resend_otp:{client_ip}", max_requests=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many resend attempts. Please wait a few minutes.")
    rec = await db.fetch_one("SELECT * FROM pending_otps WHERE otp_id = $1", body.otp_id)
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid verification session")
    user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", rec["user_id"])
    if not user:
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
    asyncio.create_task(email_service.send_auth_otp_email(user["email"], user.get("name", ""), otp))
    return {"ok": True, "message": "New verification code sent"}


@api.post("/auth/logout")
async def logout(response: Response):
    for c in ("access_token", "refresh_token", "session_token"):
        response.delete_cookie(c, path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return public_user(user)


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    tok = request.cookies.get("refresh_token")
    if not tok:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = security.decode_token(tok)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    set_jwt_cookies(response, user["user_id"], user["email"])
    return public_user(user)


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
async def reset_password(body: ResetIn):
    rec = await db.fetch_one("SELECT * FROM password_reset_tokens WHERE token = $1", body.token)
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or used token")
    if parse_dt(rec["expires_at"]) < now():
        raise HTTPException(status_code=400, detail="Token expired")
    await db.execute("UPDATE users SET password_hash = $1 WHERE user_id = $2",
                     security.hash_password(body.password), rec["user_id"])
    await db.execute("UPDATE password_reset_tokens SET used = TRUE WHERE token = $1", body.token)
    return {"ok": True}


@api.post("/auth/google/session")
async def google_session(body: GoogleSessionIn, response: Response):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                        headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()
    email = data["email"].lower()
    user = await db.fetch_one("SELECT * FROM users WHERE email = $1", email)
    if not user:
        user_id = new_id("user")
        await db.execute(
            """
            INSERT INTO users (user_id, email, name, picture, role, auth_provider, subscription_status, created_at)
            VALUES ($1, $2, $3, $4, 'seller', 'google', 'inactive', $5)
            """,
            user_id, email, data.get("name"), data.get("picture"), iso(now())
        )
        user = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", user_id)
    else:
        await db.execute(
            "UPDATE users SET name = $1, picture = $2 WHERE email = $3",
            data.get("name"), data.get("picture"), email
        )
        user = await db.fetch_one("SELECT * FROM users WHERE email = $1", email)

    session_token = data["session_token"]
    await db.execute(
        """
        INSERT INTO user_sessions (user_id, session_token, expires_at, created_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (session_token) DO UPDATE SET expires_at = EXCLUDED.expires_at
        """,
        user["user_id"], session_token, iso(now() + timedelta(days=365)), iso(now())
    )
    response.set_cookie("session_token", session_token, httponly=True, secure=True,
                        samesite="none", max_age=31536000, path="/")
    return public_user(user)


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
        return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


# ======================= Seller Route (Razorpay Partner) =======================
def _route_public(route: dict) -> dict:
    return {
        "connected": True,
        "mode": route.get("mode"),
        "status": route.get("status"),
        "accountIdLast4": (route.get("account_id") or "")[-4:],
        "beneficiaryName": route.get("beneficiary_name"),
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
    bank_last4 = body.account_number.strip()[-4:] if body.account_number and len(body.account_number.strip()) >= 4 else None

    payload = {
        "email": user["email"], "phone": clean_phone, "type": "route",
        "reference_id": store["slug"], "legal_business_name": clean_legal,
        "business_type": body.business_type, "contact_name": clean_contact,
        "profile": {"category": "ecommerce", "subcategory": "online_marketplace"},
    }
    result = await asyncio.to_thread(route_service.create_linked_account, payload)
    
    account_number_enc = security.encrypt_secret(body.account_number.strip()) if body.account_number else None
    updated_at = iso(now())

    await db.execute(
        """
        INSERT INTO seller_routes (seller_id, store_slug, account_id, mode, status, legal_business_name, contact_name, phone, beneficiary_name, account_number_enc, account_number_last4, ifsc, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (seller_id) DO UPDATE SET
            store_slug = EXCLUDED.store_slug, account_id = EXCLUDED.account_id, mode = EXCLUDED.mode,
            status = EXCLUDED.status, legal_business_name = EXCLUDED.legal_business_name,
            contact_name = EXCLUDED.contact_name, phone = EXCLUDED.phone, beneficiary_name = EXCLUDED.beneficiary_name,
            account_number_enc = EXCLUDED.account_number_enc, account_number_last4 = EXCLUDED.account_number_last4,
            ifsc = EXCLUDED.ifsc, updated_at = EXCLUDED.updated_at
        """,
        user["user_id"], store["slug"], result["account_id"], result["mode"], result["status"],
        clean_legal, clean_contact, clean_phone, clean_beneficiary, account_number_enc, bank_last4, clean_ifsc, updated_at
    )
    saved = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    return _route_public(saved)


@api.get("/seller/route")
async def get_route(user=Depends(get_current_user)):
    route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", user["user_id"])
    if not route:
        return {"connected": False}
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
@api.post("/products")
async def create_product(body: ProductIn, user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=400, detail="Create a store first")
    if body.image and not security.is_safe_image_path(body.image):
        raise HTTPException(status_code=400, detail="Invalid image path format")
    
    prod_id = new_id("prod")
    title = security.sanitize_text(body.title, 200)
    desc = security.sanitize_text(body.description, 2000)
    created_at = iso(now())
    option_groups_json = [og.model_dump() for og in body.optionGroups]

    await db.execute(
        """
        INSERT INTO products (product_id, seller_id, store_slug, title, description, price, stock, option_groups, active, image, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        prod_id, user["user_id"], store["slug"], title, desc, body.price, body.stock, option_groups_json, body.active, body.image, created_at
    )
    return {
        "product_id": prod_id, "sellerId": user["user_id"], "storeSlug": store["slug"],
        "title": title, "description": desc, "price": body.price, "stock": body.stock,
        "optionGroups": option_groups_json, "active": body.active, "image": body.image,
        "created_at": created_at,
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
    if body.image and not security.is_safe_image_path(body.image):
        raise HTTPException(status_code=400, detail="Invalid image path format")
    
    title = security.sanitize_text(body.title, 200)
    desc = security.sanitize_text(body.description, 2000)
    option_groups_json = [og.model_dump() for og in body.optionGroups]

    await db.execute(
        """
        UPDATE products
        SET title = $1, description = $2, price = $3, stock = $4, option_groups = $5, active = $6, image = $7
        WHERE product_id = $8 AND seller_id = $9
        """,
        title, desc, body.price, body.stock, option_groups_json, body.active, body.image, product_id, user["user_id"]
    )
    updated = await db.fetch_one("SELECT * FROM products WHERE product_id = $1", product_id)
    return public_product(updated)


@api.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(get_current_user)):
    res = await db.execute("DELETE FROM products WHERE product_id = $1 AND seller_id = $2", product_id, user["user_id"])
    if "0" in res:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}


# ======================= Orders =======================
async def finalize_if_expired(order: dict) -> dict:
    if order.get("status") == "delivered_confirmed":
        exp = parse_dt(order.get("windowExpiresAt"))
        if exp and now() >= exp:
            completed_at = iso(now())
            await db.execute("UPDATE orders SET status = 'completed' WHERE order_id = $1", order["order_id"])
            order["status"] = "completed"
            order["completedAt"] = completed_at
    return order


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

    order_id = new_id("ord")
    created_at = iso(now())

    # Razorpay Route Order Split Check
    route = await db.fetch_one("SELECT * FROM seller_routes WHERE seller_id = $1", store["seller_id"])
    rc, plat_kid, _ = route_service.platform_client()
    rp_order_id = None
    rp_key_id = None
    mock_payment = True

    if route and route.get("mode") == "razorpay" and route.get("account_id") and rc:
        try:
            amount_paise = int(round(total * 100))
            rp = await asyncio.to_thread(rc.order.create, {
                "amount": amount_paise, "currency": "INR", "payment_capture": 1,
                "receipt": order_id[:40],
                "transfers": [{
                    "account": route["account_id"], "amount": amount_paise, "currency": "INR",
                    "on_hold": 0, "notes": {"platform": "Stall Wise", "storeSlug": store["slug"]},
                }],
            })
            rp_order_id = rp["id"]
            rp_key_id = plat_kid
            mock_payment = False
        except Exception as e:
            logger.error(f"Razorpay Route order creation fallback: {e}")
            mock_payment = True

    await db.execute(
        """
        INSERT INTO orders (
            order_id, seller_id, store_slug, buyer_name, buyer_email, buyer_phone,
            address, items, subtotal, delivery_fee, tax, amount, status,
            razorpay_order_id, razorpay_key_id, mock_payment, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'placed', $13, $14, $15, $16
        )
        """,
        order_id, store["seller_id"], store["slug"], body.buyerName, body.buyerEmail, body.buyerPhone,
        body.address, items, total, 0, 0, total, rp_order_id, rp_key_id, mock_payment, created_at
    )

    seller = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", store["seller_id"])
    if seller:
        order_doc = {
            "order_id": order_id, "amount": total, "items": items,
            "buyerName": body.buyerName, "buyerEmail": body.buyerEmail,
        }
        asyncio.create_task(email_service.send_new_order_email(
            seller["email"], seller.get("name"), order_doc, f"{FRONTEND_URL}/orders/{order_id}"))

    return {
        "orderId": order_id,
        "amount": total,
        "razorpayOrderId": rp_order_id,
        "razorpayKeyId": rp_key_id,
        "needsMockPay": mock_payment,
    }


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

    orders = [public_order(r) for r in rows]
    return {"orders": orders, "total": total or 0, "page": page, "limit": limit,
            "pages": max(1, ((total or 0) + limit - 1) // limit)}


@api.get("/orders/{order_id}")
async def seller_order_detail(order_id: str, user=Depends(get_current_user)):
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1 AND seller_id = $2", order_id, user["user_id"])
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return public_order(o)


@api.get("/order/{order_id}")
async def buyer_order_detail(order_id: str):
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return public_order(o, for_buyer=True)


@api.post("/orders/{order_id}/mock-pay")
async def mock_pay_order(order_id: str):
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] != "placed":
        return {"status": o["status"]}
    paid_at = iso(now())
    await db.execute("UPDATE orders SET status = 'paid', paid_at = $1 WHERE order_id = $2", paid_at, order_id)
    return {"status": "paid"}


@api.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        data = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = data.get("event")
    payment = data.get("payload", {}).get("payment", {}).get("entity", {})
    rp_order_id = payment.get("order_id") or data.get("payload", {}).get("order", {}).get("entity", {}).get("id")
    
    if rp_order_id and event in ("payment.captured", "order.paid"):
        await db.execute("UPDATE orders SET status = 'paid', paid_at = $1 WHERE razorpay_order_id = $2 AND status = 'placed'",
                         iso(now()), rp_order_id)
    return {"status": "ok"}


@api.post("/orders/{order_id}/ship")
async def ship_order(order_id: str, user=Depends(get_current_user)):
    o = await db.fetch_one("SELECT * FROM orders WHERE order_id = $1 AND seller_id = $2", order_id, user["user_id"])
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] != "paid":
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
    if o["status"] not in ("shipped", "delivered_pending_otp"):
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

    delivered_at = iso(now())
    await db.execute("UPDATE orders SET status = 'delivered', delivered_at = $1 WHERE order_id = $2", delivered_at, order_id)
    return {"status": "delivered"}


# ======================= Subscription / Billing =======================
PRO_MONTHLY_AMOUNT = 499
PRO_YEARLY_AMOUNT = 4990
SUB_CURRENCY = "INR"
_PLAN_SPECS = {
    "monthly": {"period": "monthly", "interval": 1, "amount": PRO_MONTHLY_AMOUNT},
    "yearly": {"period": "yearly", "interval": 1, "amount": PRO_YEARLY_AMOUNT},
}


def platform_rp_client():
    kid = os.environ.get("RAZORPAY_KEY_ID") or os.environ.get("RAZORPAY_PLATFORM_KEY_ID")
    ksec = os.environ.get("RAZORPAY_KEY_SECRET") or os.environ.get("RAZORPAY_PLATFORM_KEY_SECRET")
    if not kid or not ksec:
        raise HTTPException(status_code=503, detail="Platform billing is not configured yet")
    return razorpay.Client(auth=(kid, ksec)), kid


@api.get("/subscription")
async def get_subscription(user=Depends(get_current_user)):
    status = await effective_sub_status(user)
    kid = os.environ.get("RAZORPAY_KEY_ID") or os.environ.get("RAZORPAY_PLATFORM_KEY_ID")
    return {
        "subscriptionStatus": status,
        "premiumTier": PREMIUM_TIER, "freeTier": FREE_TIER,
        "plans": {"monthly": PRO_MONTHLY_AMOUNT, "yearly": PRO_YEARLY_AMOUNT},
        "currency": SUB_CURRENCY,
        "billingConfigured": bool(kid),
        "subscriptionId": user.get("subscription_id") or user.get("subscriptionId"),
        "subscriptionInterval": user.get("subscription_interval") or user.get("subscriptionInterval"),
        "subscriptionExpiresAt": user.get("subscription_expires_at") or user.get("subscriptionExpiresAt"),
    }


@api.post("/subscription/simulate")
async def subscription_simulate(body: SubSimIn, user=Depends(get_current_user)):
    if body.status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be active or inactive")
    await db.execute("UPDATE users SET subscription_status = $1 WHERE user_id = $2", body.status, user["user_id"])
    return {"subscriptionStatus": body.status}


@api.get("/")
async def root():
    return {"service": "Stall Wise API", "status": "ok", "engine": "PostgreSQL"}


app.include_router(api)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Production static assets mounting for single-service Railway deployment
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist"))
if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("uploads"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = os.path.join(DIST_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(DIST_DIR, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not found")

cors_origins = [FRONTEND_URL, "http://localhost:3000"]
if os.environ.get("EXTRA_CORS_ORIGINS"):
    cors_origins.extend([o.strip() for o in os.environ["EXTRA_CORS_ORIGINS"].split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.railway\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================= Startup: indexes + seed =======================
async def ensure_seller(email, password, name, slug, store_name):
    u = await db.fetch_one("SELECT * FROM users WHERE email = $1", email.lower())
    if not u:
        user_id = new_id("user")
        await db.execute(
            """
            INSERT INTO users (user_id, email, name, password_hash, role, auth_provider, subscription_status, created_at)
            VALUES ($1, $2, $3, $4, 'seller', 'password', 'active', $5)
            """,
            user_id, email.lower(), name, security.hash_password(password), iso(now())
        )
        u = await db.fetch_one("SELECT * FROM users WHERE user_id = $1", user_id)
    
    s = await db.fetch_one("SELECT * FROM stores WHERE seller_id = $1", u["user_id"])
    if not s:
        existing_slug = await db.fetch_one("SELECT * FROM stores WHERE slug = $1", slug)
        if not existing_slug:
            await db.execute(
                """
                INSERT INTO stores (store_id, seller_id, name, slug, bio, acceptance_window_minutes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                new_id("store"), u["user_id"], store_name, slug,
                "Handcrafted goods shipped fresh directly to your door.", DEFAULT_WINDOW_MIN, iso(now())
            )
    return u


async def seed():
    admin_email = os.environ.get("ADMIN_EMAIL", "dassantana135@gmail.com")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "Admin@StallWise2026")
    owner = await ensure_seller(admin_email, admin_pass, "Stall Wise Merchant", "demo-store", "Demo Store")
    await ensure_seller("artisan@stallwise.in", "Artisan@2026", "Artisan Studio", "artisan-shop", "Artisan Shop")

    prod_count = await db.fetch_val("SELECT COUNT(*) FROM products WHERE store_slug = 'demo-store'")
    if not prod_count:
        await db.execute(
            """
            INSERT INTO products (product_id, seller_id, store_slug, title, description, price, stock, option_groups, active, created_at)
            VALUES 
            ($1, $2, 'demo-store', 'Organic Honey (500g)', 'Raw wildflower honey, harvested locally.', 350.0, 40, '[]'::jsonb, TRUE, $3),
            ($4, $2, 'demo-store', 'Cotton Artisan T-Shirt', 'Handmade, soft breathable organic cotton.', 600.0, 50, $5, TRUE, $3)
            """,
            new_id("prod"), owner["user_id"], iso(now()),
            new_id("prod"),
            json.dumps([{
                "name": "Size",
                "options": [
                    {"label": "S", "priceDelta": 0, "stock": 10},
                    {"label": "M", "priceDelta": 0, "stock": 25},
                    {"label": "L", "priceDelta": 50, "stock": 15}
                ]
            }])
        )


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
        if db._pool:
            await seed()
            logger.info("Stall Wise startup seed complete")
    except Exception as e:
        logger.error(f"seed error: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    await db.close_db()
