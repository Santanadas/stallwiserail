from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import re
import uuid
import logging
import hashlib
import hmac
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict

import httpx
import razorpay
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, Query, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

import security
import email_service
import storage
import route_service

# ---------- DB ----------
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
PREMIUM_TIER = "Stall Wise Pro"
FREE_TIER = "Community"
DEFAULT_WINDOW_MIN = 120
OTP_EXPIRY_MIN = 4320  # 3 days
OTP_MAX_ATTEMPTS = 5
AUTH_OTP_EXPIRY_MIN = 10
AUTH_OTP_MAX_ATTEMPTS = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marketo")

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
    dt = datetime.fromisoformat(v)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


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
    price: float = Field(ge=0.0, le=10000000.0)
    stock: Optional[int] = Field(default=None, ge=0, le=100000)
    optionGroups: List[OptionGroupIn] = Field(default=[], max_length=10)
    active: bool = True
    image: Optional[str] = Field(default=None, max_length=1000)


class OrderItemIn(BaseModel):
    productId: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=1000)
    optionSelections: Dict[str, str] = Field(default={})


class OrderIn(BaseModel):
    storeSlug: str = Field(min_length=1, max_length=60)
    buyerName: str = Field(min_length=1, max_length=100)
    buyerEmail: EmailStr
    items: List[OrderItemIn] = Field(min_length=1, max_length=50)
    acceptanceWindowMinutes: Optional[int] = Field(default=None, ge=1, le=10080)


class OtpIn(BaseModel):
    otp: str = Field(min_length=4, max_length=12)


class VerifyOtpIn(BaseModel):
    otp_id: str = Field(min_length=1, max_length=64)
    otp: str = Field(min_length=6, max_length=6)


class ResendOtpIn(BaseModel):
    otp_id: str = Field(min_length=1, max_length=64)


class DisputeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


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
    # 6-month (180 days) access token, 1-year (365 days) refresh token for persistent sessions
    resp.set_cookie("access_token", security.create_access_token(user_id, email),
                    httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE, max_age=15552000, path="/")
    resp.set_cookie("refresh_token", security.create_refresh_token(user_id),
                    httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE, max_age=31536000, path="/")


def public_user(u: dict) -> dict:
    return {
        "user_id": u["user_id"], "email": u["email"], "name": u.get("name"),
        "role": u.get("role", "seller"), "authProvider": u.get("authProvider", "password"),
        "subscriptionStatus": u.get("subscriptionStatus", "inactive"),
        "picture": u.get("picture"),
        "avatar": u.get("avatar"),
    }


async def _resolve_user(token: str):
    if not token:
        return None
    try:
        payload = security.decode_token(token)
        if payload.get("type") == "access":
            u = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
            if u:
                return u
    except Exception:
        pass
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if sess:
        exp = parse_dt(sess.get("expires_at"))
        if exp and exp > now():
            return await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
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


# ======================= Auth OTP helper =======================
async def _create_auth_otp(user_id: str, email: str, name: str, purpose: str) -> dict:
    """Generate a 6-digit OTP for auth verification, store it, and email it."""
    otp = security.generate_otp()
    otp_id = new_id("otp")
    await db.pending_otps.insert_one({
        "otp_id": otp_id,
        "user_id": user_id,
        "email": email,
        "otp_hash": security.hash_otp(otp),
        "purpose": purpose,  # "register" or "login"
        "attempts": 0,
        "locked": False,
        "created_at": iso(now()),
        "expires_at": iso(now() + timedelta(minutes=AUTH_OTP_EXPIRY_MIN)),
    })
    try:
        await email_service.send_auth_otp_email(email, name, otp)
    except Exception as e:
        logger.error(f"auth OTP email failed: {e}")
    logger.info(f"Auth OTP for {email} ({purpose}): {otp}")
    return {"otp_id": otp_id}


# ======================= Auth routes =======================
@api.post("/auth/register")
async def register(body: RegisterIn, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    if not security.check_rate_limit(f"reg:{client_ip}", max_requests=10, window_seconds=900):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = new_id("user")
    clean_name = security.sanitize_text(body.name, 100)
    doc = {
        "user_id": user_id, "email": email, "name": clean_name,
        "password_hash": security.hash_password(body.password),
        "role": "seller", "authProvider": "password",
        "subscriptionStatus": "inactive", "created_at": iso(now()),
    }
    await db.users.insert_one(doc)
    otp_info = await _create_auth_otp(user_id, email, clean_name, "register")
    return {"pendingOtp": True, "email": email, "otpId": otp_info["otp_id"]}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ident = f"{request.client.host}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5:
        locked_until = parse_dt(att.get("locked_until"))
        if locked_until and locked_until > now():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not security.verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": ident},
            {"$inc": {"count": 1}, "$set": {"locked_until": iso(now() + timedelta(minutes=15))}},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    otp_info = await _create_auth_otp(user["user_id"], email, user.get("name", ""), "login")
    return {"pendingOtp": True, "email": email, "otpId": otp_info["otp_id"]}


@api.post("/auth/verify-otp")
async def verify_auth_otp(body: VerifyOtpIn, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    if not security.check_rate_limit(f"auth_otp:{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait.")
    rec = await db.pending_otps.find_one({"otp_id": body.otp_id})
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
        await db.pending_otps.update_one(
            {"otp_id": body.otp_id},
            {"$set": {"attempts": attempts, "locked": locked}},
        )
        if locked:
            raise HTTPException(status_code=423, detail="Too many failed attempts. Please request a new code.")
        raise HTTPException(status_code=400, detail=f"Invalid code ({attempts}/{AUTH_OTP_MAX_ATTEMPTS} attempts)")
    # OTP verified — issue JWT cookies
    user = await db.users.find_one({"user_id": rec["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.pending_otps.delete_one({"otp_id": body.otp_id})
    set_jwt_cookies(response, user["user_id"], user["email"])
    return public_user(user)


@api.post("/auth/resend-otp")
async def resend_auth_otp(body: ResendOtpIn, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not security.check_rate_limit(f"resend_otp:{client_ip}", max_requests=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many resend attempts. Please wait a few minutes.")
    rec = await db.pending_otps.find_one({"otp_id": body.otp_id})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid verification session")
    user = await db.users.find_one({"user_id": rec["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification session")
    # Delete old and create fresh OTP
    await db.pending_otps.delete_one({"otp_id": body.otp_id})
    otp_info = await _create_auth_otp(user["user_id"], user["email"], user.get("name", ""), rec.get("purpose", "login"))
    return {"ok": True, "otpId": otp_info["otp_id"], "message": "A new code has been sent to your email."}


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
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    set_jwt_cookies(response, user["user_id"], user["email"])
    return public_user(user)


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotIn, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not security.check_rate_limit(f"forgot:{client_ip}", max_requests=6, window_seconds=900):
        raise HTTPException(status_code=429, detail="Too many password reset attempts. Please try again later.")
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if user and user.get("authProvider") == "password":
        import secrets as _s
        token = _s.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token, "user_id": user["user_id"],
            "expires_at": iso(now() + timedelta(hours=1)), "used": False,
        })
        link = f"{FRONTEND_URL}/reset-password?token={token}"
        logger.info(f"Password reset link: {link}")
        await email_service.send_reset_email(email, link)
    return {"ok": True, "message": "If that email exists, a reset link was sent."}


@api.post("/auth/reset-password")
async def reset_password(body: ResetIn):
    rec = await db.password_reset_tokens.find_one({"token": body.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or used token")
    if parse_dt(rec["expires_at"]) < now():
        raise HTTPException(status_code=400, detail="Token expired")
    await db.users.update_one({"user_id": rec["user_id"]},
                              {"$set": {"password_hash": security.hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
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
    user = await db.users.find_one({"email": email})
    if not user:
        user_id = new_id("user")
        user = {
            "user_id": user_id, "email": email, "name": data.get("name"),
            "picture": data.get("picture"), "role": "seller", "authProvider": "google",
            "subscriptionStatus": "inactive", "created_at": iso(now()),
        }
        await db.users.insert_one(user)
    else:
        await db.users.update_one({"email": email},
                                  {"$set": {"name": data.get("name"), "picture": data.get("picture")}})
    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user["user_id"], "session_token": session_token,
        "expires_at": iso(now() + timedelta(days=365)), "created_at": iso(now()),
    })
    response.set_cookie("session_token", session_token, httponly=True, secure=True,
                        samesite="none", max_age=31536000, path="/")
    return public_user(user)


# ======================= Store routes =======================
async def get_my_store(user):
    store = await db.stores.find_one({"sellerId": user["user_id"]}, {"_id": 0})
    return store


@api.post("/stores")
async def create_store(body: StoreIn, user=Depends(get_current_user)):
    slug = body.slug.lower().strip()
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Slug must be lowercase letters, numbers and hyphens")
    if await db.stores.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="Slug already taken")
    if await get_my_store(user):
        raise HTTPException(status_code=400, detail="You already have a store")
    doc = {
        "store_id": new_id("store"), "sellerId": user["user_id"],
        "name": security.sanitize_text(body.name, 100),
        "slug": slug,
        "bio": security.sanitize_text(body.bio, 500),
        "acceptanceWindowMinutes": body.acceptanceWindowMinutes,
        "created_at": iso(now()),
    }
    await db.stores.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/stores/me")
async def my_store(user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        return None
    rp = await db.seller_gateways.find_one({"sellerId": user["user_id"]}, {"_id": 0})
    store["razorpayConnected"] = bool(rp)
    route = await db.seller_routes.find_one({"sellerId": user["user_id"]}, {"_id": 0})
    store["routeConnected"] = bool(route)
    store["routeStatus"] = route.get("status") if route else None
    store["routeMode"] = route.get("mode") if route else None
    return store


@api.put("/stores/me")
async def update_store(body: StoreUpdateIn, user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=404, detail="No store")
    upd = {}
    if body.name is not None:
        upd["name"] = security.sanitize_text(body.name, 100)
    if body.bio is not None:
        upd["bio"] = security.sanitize_text(body.bio, 500)
    if body.acceptanceWindowMinutes is not None:
        upd["acceptanceWindowMinutes"] = body.acceptanceWindowMinutes
    if upd:
        await db.stores.update_one({"store_id": store["store_id"]}, {"$set": upd})
    return await get_my_store(user)


async def effective_sub_status(seller: dict) -> str:
    """Downgrade to inactive when a one-time Pro period has expired."""
    status = seller.get("subscriptionStatus", "inactive")
    exp = seller.get("subscriptionExpiresAt")
    if status == "active" and exp and parse_dt(exp) < now():
        await db.users.update_one({"user_id": seller["user_id"]},
                                  {"$set": {"subscriptionStatus": "inactive"}})
        return "inactive"
    return status


@api.get("/shop/{slug}")
async def public_shop(slug: str):
    store = await db.stores.find_one({"slug": slug.lower()}, {"_id": 0})
    if not store:
        raise HTTPException(status_code=404, detail="Shop not found")
    seller = await db.users.find_one({"user_id": store["sellerId"]}, {"_id": 0})
    products = await db.products.find(
        {"storeSlug": slug.lower(), "active": True}, {"_id": 0}
    ).to_list(500)
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
    await db.files.insert_one({
        "id": new_id("file"), "storage_path": stored, "content_type": content_type,
        "sellerId": user["user_id"], "size": result.get("size"), "is_deleted": False,
        "created_at": iso(now()),
    })
    if kind == "avatar":
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"avatar": stored}})
    return {"path": stored, "url": f"/api/files/{stored}"}


@api.delete("/uploads/avatar")
async def delete_avatar(user=Depends(get_current_user)):
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"avatar": None}})
    return {"ok": True}


@api.get("/files/{path:path}")
async def serve_file(path: str):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = await asyncio.to_thread(storage.get_object, path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=data, media_type=rec.get("content_type") or content_type,
                    headers={"Cache-Control": "public, max-age=86400"})


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
    if result.get("mode") == "error":
        raise HTTPException(status_code=502, detail=result.get("detail") or "Could not onboard seller")
    doc = {
        "sellerId": user["user_id"], "storeSlug": store["slug"],
        "account_id": result["account_id"], "mode": result["mode"], "status": result["status"],
        "legal_business_name": clean_legal, "contact_name": clean_contact,
        "phone": clean_phone, "beneficiary_name": clean_beneficiary,
        "account_number_enc": security.encrypt_secret(body.account_number.strip()) if body.account_number else None,
        "account_number_last4": bank_last4,
        "ifsc": clean_ifsc, "updated_at": iso(now()),
    }
    await db.seller_routes.update_one({"sellerId": user["user_id"]}, {"$set": doc}, upsert=True)
    saved = await db.seller_routes.find_one({"sellerId": user["user_id"]}, {"_id": 0})
    return _route_public(saved)


@api.get("/seller/route")
async def get_route(user=Depends(get_current_user)):
    route = await db.seller_routes.find_one({"sellerId": user["user_id"]}, {"_id": 0})
    if not route:
        return {"connected": False}
    return _route_public(route)


@api.delete("/seller/route")
async def disconnect_route(user=Depends(get_current_user)):
    await db.seller_routes.delete_one({"sellerId": user["user_id"]})
    return {"connected": False}


# ======================= Seller gateway =======================
@api.post("/seller/razorpay")
async def connect_razorpay(body: RazorpayIn, user=Depends(get_current_user)):
    doc = {
        "sellerId": user["user_id"], "key_id": body.key_id,
        "key_secret_enc": security.encrypt_secret(body.key_secret),
        "webhook_secret_enc": security.encrypt_secret(body.webhook_secret) if body.webhook_secret else None,
        "updated_at": iso(now()),
    }
    await db.seller_gateways.update_one({"sellerId": user["user_id"]}, {"$set": doc}, upsert=True)
    return {"connected": True, "key_id_last4": body.key_id[-4:]}


@api.get("/seller/razorpay")
async def get_razorpay(user=Depends(get_current_user)):
    rp = await db.seller_gateways.find_one({"sellerId": user["user_id"]}, {"_id": 0})
    if not rp:
        return {"connected": False}
    return {"connected": True, "key_id_last4": rp["key_id"][-4:],
            "webhookConfigured": bool(rp.get("webhook_secret_enc"))}


@api.delete("/seller/razorpay")
async def disconnect_razorpay(user=Depends(get_current_user)):
    await db.seller_gateways.delete_one({"sellerId": user["user_id"]})
    return {"connected": False}


# ======================= Products =======================
@api.post("/products")
async def create_product(body: ProductIn, user=Depends(get_current_user)):
    store = await get_my_store(user)
    if not store:
        raise HTTPException(status_code=400, detail="Create a store first")
    if body.image and not security.is_safe_image_path(body.image):
        raise HTTPException(status_code=400, detail="Invalid image path format")
    doc = body.model_dump()
    doc["title"] = security.sanitize_text(body.title, 200)
    doc["description"] = security.sanitize_text(body.description, 2000)
    doc.update({"product_id": new_id("prod"), "sellerId": user["user_id"],
                "storeSlug": store["slug"], "created_at": iso(now())})
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/products")
async def my_products(user=Depends(get_current_user)):
    return await db.products.find({"sellerId": user["user_id"]}, {"_id": 0}).to_list(500)


@api.put("/products/{product_id}")
async def update_product(product_id: str, body: ProductIn, user=Depends(get_current_user)):
    prod = await db.products.find_one({"product_id": product_id, "sellerId": user["user_id"]})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    if body.image and not security.is_safe_image_path(body.image):
        raise HTTPException(status_code=400, detail="Invalid image path format")
    upd = body.model_dump()
    upd["title"] = security.sanitize_text(body.title, 200)
    upd["description"] = security.sanitize_text(body.description, 2000)
    await db.products.update_one({"product_id": product_id}, {"$set": upd})
    return await db.products.find_one({"product_id": product_id}, {"_id": 0})


@api.delete("/products/{product_id}")
async def delete_product(product_id: str, user=Depends(get_current_user)):
    res = await db.products.delete_one({"product_id": product_id, "sellerId": user["user_id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}


# ======================= Orders =======================
def sanitize_order(o: dict, for_buyer=False) -> dict:
    o = dict(o)
    o.pop("_id", None)
    o.pop("otpCodeHash", None)
    otp_enc = o.pop("otpEnc", None)
    if for_buyer and otp_enc:
        try:
            o["otp"] = security.decrypt_secret(otp_enc)
        except Exception:
            pass
    return o


async def finalize_if_expired(order: dict) -> dict:
    if order.get("status") == "delivered_confirmed":
        exp = parse_dt(order.get("windowExpiresAt"))
        if exp and now() >= exp:
            await db.orders.update_one({"order_id": order["order_id"]},
                                       {"$set": {"status": "completed", "completedAt": iso(now())}})
            order["status"] = "completed"
            order["completedAt"] = iso(now())
    return order


@api.post("/orders")
async def create_order(body: OrderIn, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not security.check_rate_limit(f"order:{client_ip}", max_requests=30, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many orders placed. Please try again in a few minutes.")

    store = await db.stores.find_one({"slug": body.storeSlug.lower().strip()}, {"_id": 0})
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    items = []
    total = 0.0
    prod_cache = {}
    demand = {}  # product_id -> {"product_qty": int, "options": {group: {label: qty}}}
    for it in body.items:
        if it.quantity < 1 or it.quantity > 1000:
            raise HTTPException(status_code=400, detail="Invalid item quantity")
        prod = prod_cache.get(it.productId)
        if prod is None:
            prod = await db.products.find_one({"product_id": it.productId, "active": True}, {"_id": 0})
            if not prod or prod["storeSlug"] != store["slug"]:
                raise HTTPException(status_code=400, detail=f"Invalid product {it.productId}")
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

    if total < 0:
        raise HTTPException(status_code=400, detail="Total order amount cannot be negative")

    # Stock check (block sell-outs). stock=None means unlimited.
    for pid, need in demand.items():
        prod = prod_cache[pid]
        if prod.get("stock") is not None and need["product_qty"] > prod["stock"]:
            raise HTTPException(status_code=409,
                                detail=f"Out of stock: {prod['title']} (only {prod['stock']} left)")
        for g in prod.get("optionGroups", []):
            for label, qty in need["options"].get(g["name"], {}).items():
                opt = next((o for o in g["options"] if o["label"] == label), None)
                if opt and opt.get("stock") is not None and qty > opt["stock"]:
                    raise HTTPException(status_code=409,
                                        detail=f"Out of stock: {prod['title']} — {g['name']} {label} (only {opt['stock']} left)")

    # Decrement stock
    for pid, need in demand.items():
        prod = prod_cache[pid]
        set_doc = {}
        if prod.get("stock") is not None:
            set_doc["stock"] = prod["stock"] - need["product_qty"]
        groups = prod.get("optionGroups", [])
        changed = False
        for g in groups:
            for o in g["options"]:
                q = need["options"].get(g["name"], {}).get(o["label"])
                if q and o.get("stock") is not None:
                    o["stock"] = o["stock"] - q
                    changed = True
        if changed:
            set_doc["optionGroups"] = groups
        if set_doc:
            await db.products.update_one({"product_id": pid}, {"$set": set_doc})

    clean_buyer_name = security.sanitize_text(body.buyerName, 100)
    window = body.acceptanceWindowMinutes or store.get("acceptanceWindowMinutes", DEFAULT_WINDOW_MIN)
    order_id = new_id("ord")
    doc = {
        "order_id": order_id, "buyerName": clean_buyer_name, "buyerEmail": body.buyerEmail.lower().strip(),
        "sellerId": store["sellerId"], "storeSlug": store["slug"], "items": items,
        "amount": round(total, 2), "status": "placed",
        "otpCodeHash": None, "otpEnc": None, "otpGeneratedAt": None, "otpAttempts": 0,
        "otpLocked": False, "deliveryConfirmedAt": None,
        "acceptanceWindowMinutes": window, "windowExpiresAt": None,
        "disputeRaised": False, "disputeReason": None,
        "razorpayOrderId": None, "razorpayKeyId": None, "mockPayment": False, "created_at": iso(now()),
    }

    route = await db.seller_routes.find_one({"sellerId": store["sellerId"]})
    rc, plat_kid, _ = route_service.platform_client()
    rp_order_id = None
    rp_key_id = None
    if route and route.get("mode") == "razorpay" and route.get("account_id") and rc:
        try:
            amount_paise = int(round(total * 100))
            rp = await asyncio.to_thread(rc.order.create, {
                "amount": amount_paise, "currency": "INR", "payment_capture": 1,
                "receipt": order_id[:40],
                "transfers": [{
                    "account": route["account_id"], "amount": amount_paise, "currency": "INR",
                    "on_hold": 0, "notes": {"platform": "Peddle Cart", "storeSlug": store["slug"]},
                }],
            })
            rp_order_id = rp["id"]
            rp_key_id = plat_kid
            doc["razorpayOrderId"] = rp_order_id
            doc["razorpayKeyId"] = rp_key_id
        except Exception as e:
            logger.error(f"Razorpay Route order creation failed: {e}")
            doc["mockPayment"] = True
    else:
        doc["mockPayment"] = True

    await db.orders.insert_one(doc)

    seller = await db.users.find_one({"user_id": store["sellerId"]}, {"_id": 0})
    if seller:
        try:
            await email_service.send_new_order_email(
                seller["email"], seller.get("name"), doc, f"{FRONTEND_URL}/orders/{order_id}")
        except Exception as e:
            logger.error(f"order email failed: {e}")

    return {"orderId": order_id, "amount": doc["amount"], "razorpayOrderId": rp_order_id,
            "razorpayKeyId": rp_key_id, "needsMockPay": doc["mockPayment"]}


@api.get("/orders")
async def list_orders(status: Optional[str] = Query(None),
                      page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100),
                      user=Depends(get_current_user)):
    q = {"sellerId": user["user_id"]}
    if status:
        q["status"] = status
    total = await db.orders.count_documents(q)
    skip = (page - 1) * limit
    orders = await db.orders.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    out = []
    for o in orders:
        o = await finalize_if_expired(o)
        out.append(sanitize_order(o))
    return {"orders": out, "total": total, "page": page, "limit": limit,
            "pages": max(1, (total + limit - 1) // limit)}


@api.get("/orders/{order_id}")
async def seller_order_detail(order_id: str, user=Depends(get_current_user)):
    o = await db.orders.find_one({"order_id": order_id, "sellerId": user["user_id"]})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o = await finalize_if_expired(o)
    return sanitize_order(o)


@api.get("/buyer/orders/{order_id}")
async def buyer_order_detail(order_id: str, email: str = Query(...), request: Request = None):
    client_ip = request.client.host if request and request.client else "unknown"
    if not security.check_rate_limit(f"buyer_ord:{client_ip}", max_requests=40, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    o = await db.orders.find_one({"order_id": order_id})
    if not o or o["buyerEmail"] != email.lower().strip():
        raise HTTPException(status_code=404, detail="Order not found")
    o = await finalize_if_expired(o)
    return sanitize_order(o, for_buyer=True)


@api.post("/orders/{order_id}/simulate-payment")
async def simulate_payment(order_id: str):
    """MOCKED payment success for testing ONLY when mockPayment is explicitly true."""
    o = await db.orders.find_one({"order_id": order_id})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if not o.get("mockPayment"):
        raise HTTPException(status_code=403, detail="Payment simulation is only allowed on mock-payment orders")
    if o["status"] != "placed":
        raise HTTPException(status_code=400, detail="Order is not awaiting payment")
    await db.orders.update_one({"order_id": order_id},
                               {"$set": {"status": "paid", "paidAt": iso(now())}})
    return {"status": "paid"}


@api.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")
    entity = (((data.get("payload") or {}).get("payment") or {}).get("entity") or {})
    rp_order_id = entity.get("order_id")
    if not rp_order_id:
        return {"status": "ignored"}
    order = await db.orders.find_one({"razorpayOrderId": rp_order_id})
    if not order:
        return {"status": "ignored"}

    verified = False
    gateway = await db.seller_gateways.find_one({"sellerId": order["sellerId"]})
    if gateway and gateway.get("webhook_secret_enc"):
        try:
            secret = security.decrypt_secret(gateway["webhook_secret_enc"])
            expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, signature):
                verified = True
            else:
                raise HTTPException(status_code=400, detail="Invalid seller gateway webhook signature")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    # If seller doesn't have custom webhook secret, check platform webhook secret
    platform_secret = os.environ.get("RAZORPAY_PLATFORM_WEBHOOK_SECRET") or os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not verified and platform_secret:
        try:
            expected = hmac.new(platform_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, signature):
                verified = True
            else:
                raise HTTPException(status_code=400, detail="Invalid platform webhook signature")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    # In production with live payments, signature verification must pass
    if not verified and not order.get("mockPayment"):
        if not signature:
            raise HTTPException(status_code=400, detail="Missing webhook signature")

    if data.get("event") in ("payment.captured", "order.paid") and order["status"] == "placed":
        await db.orders.update_one({"order_id": order["order_id"]},
                                   {"$set": {"status": "paid", "paidAt": iso(now())}})
    return {"status": "ok"}


@api.post("/orders/{order_id}/ship")
async def ship_order(order_id: str, user=Depends(get_current_user)):
    o = await db.orders.find_one({"order_id": order_id, "sellerId": user["user_id"]})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before shipping")
    otp = security.generate_otp()
    await db.orders.update_one({"order_id": order_id}, {"$set": {
        "status": "shipped", "otpCodeHash": security.hash_otp(otp),
        "otpEnc": security.encrypt_secret(otp), "otpGeneratedAt": iso(now()),
        "otpAttempts": 0, "otpLocked": False, "shippedAt": iso(now()),
    }})
    try:
        await email_service.send_otp_email(o["buyerEmail"], o["buyerName"], otp,
                                            f"{FRONTEND_URL}/order/{order_id}")
    except Exception as e:
        logger.error(f"otp email failed: {e}")
    return {"status": "shipped"}


@api.post("/orders/{order_id}/out-for-delivery")
async def out_for_delivery(order_id: str, user=Depends(get_current_user)):
    o = await db.orders.find_one({"order_id": order_id, "sellerId": user["user_id"]})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] != "shipped":
        raise HTTPException(status_code=400, detail="Order must be shipped first")
    await db.orders.update_one({"order_id": order_id}, {"$set": {"status": "delivered_pending_otp"}})
    return {"status": "delivered_pending_otp"}


@api.post("/orders/{order_id}/confirm-delivery")
async def confirm_delivery(order_id: str, body: OtpIn, request: Request, user=Depends(get_current_user)):
    client_ip = request.client.host if request.client else "unknown"
    if not security.check_rate_limit(f"otp_conf:{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait a moment.")

    o = await db.orders.find_one({"order_id": order_id, "sellerId": user["user_id"]})
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o["status"] not in ("shipped", "delivered_pending_otp"):
        raise HTTPException(status_code=400, detail="Order not ready for delivery confirmation")
    if o.get("otpLocked"):
        raise HTTPException(status_code=423, detail="OTP locked after too many failed attempts")
    gen = parse_dt(o.get("otpGeneratedAt"))
    if not o.get("otpCodeHash") or not gen:
        raise HTTPException(status_code=400, detail="No OTP issued for this order")
    if now() > gen + timedelta(minutes=OTP_EXPIRY_MIN):
        raise HTTPException(status_code=400, detail="OTP expired")
    if not security.verify_otp(body.otp.strip(), o["otpCodeHash"]):
        attempts = o.get("otpAttempts", 0) + 1
        locked = attempts >= OTP_MAX_ATTEMPTS
        await db.orders.update_one({"order_id": order_id},
                                   {"$set": {"otpAttempts": attempts, "otpLocked": locked}})
        detail = "OTP locked after too many failed attempts" if locked else f"Invalid OTP ({attempts}/{OTP_MAX_ATTEMPTS})"
        raise HTTPException(status_code=400, detail=detail)
    confirmed = now()
    window = o.get("acceptanceWindowMinutes", DEFAULT_WINDOW_MIN)
    await db.orders.update_one({"order_id": order_id}, {"$set": {
        "status": "delivered_confirmed", "deliveryConfirmedAt": iso(confirmed),
        "windowExpiresAt": iso(confirmed + timedelta(minutes=window)),
    }})
    return {"status": "delivered_confirmed", "windowExpiresAt": iso(confirmed + timedelta(minutes=window))}


@api.post("/buyer/orders/{order_id}/dispute")
async def raise_dispute(order_id: str, body: DisputeIn, email: str = Query(...)):
    o = await db.orders.find_one({"order_id": order_id})
    if not o or o["buyerEmail"] != email.lower().strip():
        raise HTTPException(status_code=404, detail="Order not found")
    o = await finalize_if_expired(o)
    if o["status"] == "completed":
        raise HTTPException(status_code=400, detail="Acceptance window has closed. No refunds possible.")
    if o["status"] != "delivered_confirmed":
        raise HTTPException(status_code=400, detail="Disputes are only allowed after delivery is confirmed")
    exp = parse_dt(o.get("windowExpiresAt"))
    if exp and now() >= exp:
        raise HTTPException(status_code=400, detail="Acceptance window has closed. No refunds possible.")
    clean_reason = security.sanitize_text(body.reason, 1000)
    await db.orders.update_one({"order_id": order_id}, {"$set": {
        "status": "disputed", "disputeRaised": True, "disputeReason": clean_reason,
        "disputedAt": iso(now()),
    }})
    return {"status": "disputed"}


# ======================= Subscription (MOCKED checkout) =======================
# ======================= Subscription (real Razorpay Subscriptions) =======================
PRO_MONTHLY_AMOUNT = int(os.environ.get("MARKETO_PRO_MONTHLY_PRICE", "199"))
PRO_YEARLY_AMOUNT = int(os.environ.get("MARKETO_PRO_YEARLY_PRICE", "999"))
SUB_CURRENCY = "INR"
_PLAN_SPECS = {
    "monthly": {"period": "monthly", "interval": 1, "amount": PRO_MONTHLY_AMOUNT, "total_count": 120},
    "yearly": {"period": "yearly", "interval": 1, "amount": PRO_YEARLY_AMOUNT, "total_count": 10},
}


def platform_rp_client():
    kid = os.environ.get("RAZORPAY_PLATFORM_KEY_ID")
    ksec = os.environ.get("RAZORPAY_PLATFORM_KEY_SECRET")
    if not kid or not ksec:
        raise HTTPException(status_code=503, detail="Platform billing is not configured yet")
    return razorpay.Client(auth=(kid, ksec)), kid


async def ensure_plan(rc, interval):
    spec = _PLAN_SPECS[interval]
    existing = await db.platform_plans.find_one({"interval": interval, "amount": spec["amount"]}, {"_id": 0})
    if existing:
        return existing["plan_id"]
    plan = await asyncio.to_thread(rc.plan.create, {
        "period": spec["period"], "interval": spec["interval"],
        "item": {"name": f"{PREMIUM_TIER} ({interval})", "amount": spec["amount"] * 100, "currency": SUB_CURRENCY},
    })
    await db.platform_plans.update_one({"interval": interval, "amount": spec["amount"]},
                                       {"$set": {"plan_id": plan["id"]}}, upsert=True)
    return plan["id"]


@api.get("/subscription")
async def get_subscription(user=Depends(get_current_user)):
    status = await effective_sub_status(user)
    return {
        "subscriptionStatus": status,
        "premiumTier": PREMIUM_TIER, "freeTier": FREE_TIER,
        "plans": {"monthly": PRO_MONTHLY_AMOUNT, "yearly": PRO_YEARLY_AMOUNT},
        "currency": SUB_CURRENCY,
        "billingConfigured": bool(os.environ.get("RAZORPAY_PLATFORM_KEY_ID")),
        "subscriptionId": user.get("subscriptionId"),
        "subscriptionInterval": user.get("subscriptionInterval"),
        "subscriptionExpiresAt": user.get("subscriptionExpiresAt"),
    }


@api.post("/subscription/create")
async def subscription_create(body: SubCreateIn, user=Depends(get_current_user)):
    if body.interval not in _PLAN_SPECS:
        raise HTTPException(status_code=400, detail="interval must be monthly or yearly")
    rc, kid = platform_rp_client()
    spec = _PLAN_SPECS[body.interval]
    # Preferred: real auto-recurring Razorpay Subscription (requires Subscriptions enabled on the account)
    try:
        plan_id = await ensure_plan(rc, body.interval)
        sub = await asyncio.to_thread(rc.subscription.create, {
            "plan_id": plan_id, "total_count": spec["total_count"], "customer_notify": 1,
            "notes": {"user_id": user["user_id"], "email": user["email"]},
        })
        await db.users.update_one({"user_id": user["user_id"]},
                                  {"$set": {"subscriptionId": sub["id"], "subscriptionInterval": body.interval}})
        return {"mode": "subscription", "subscriptionId": sub["id"], "keyId": kid, "tier": PREMIUM_TIER,
                "amount": spec["amount"], "currency": SUB_CURRENCY, "interval": body.interval}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Razorpay Subscriptions unavailable ({type(e).__name__}); using one-time order fallback")

    # Fallback: one-time Order that grants a Pro period on payment (works when Subscriptions isn't enabled)
    try:
        order = await asyncio.to_thread(rc.order.create, {
            "amount": spec["amount"] * 100, "currency": SUB_CURRENCY, "payment_capture": 1,
            "notes": {"user_id": user["user_id"], "kind": "marketo_pro", "interval": body.interval},
        })
    except Exception as e:
        logger.error(f"one-time pro order failed: {type(e).__name__}: {e!r}")
        raise HTTPException(status_code=502, detail="Could not start payment")
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"proOrderId": order["id"], "proOrderInterval": body.interval}})
    return {"mode": "onetime", "orderId": order["id"], "keyId": kid, "tier": PREMIUM_TIER,
            "amount": spec["amount"], "currency": SUB_CURRENCY, "interval": body.interval}


@api.post("/subscription/verify-payment")
async def verify_payment(body: PayVerifyIn, user=Depends(get_current_user)):
    rc, kid = platform_rp_client()
    if user.get("proOrderId") != body.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Unknown order")
    try:
        rc.utility.verify_payment_signature({
            "razorpay_order_id": body.razorpay_order_id,
            "razorpay_payment_id": body.razorpay_payment_id,
            "razorpay_signature": body.razorpay_signature,
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    interval = user.get("proOrderInterval", "monthly")
    days = 365 if interval == "yearly" else 30
    expires = now() + timedelta(days=days)
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {
        "subscriptionStatus": "active", "subscriptionExpiresAt": iso(expires),
        "subscriptionInterval": interval,
    }})
    return {"subscriptionStatus": "active", "expiresAt": iso(expires)}


@api.post("/webhooks/razorpay-subscription")
async def razorpay_subscription_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    secret = os.environ.get("RAZORPAY_SUBSCRIPTION_WEBHOOK_SECRET")
    if secret:
        try:
            razorpay.Client(auth=("", "")).utility.verify_webhook_signature(payload.decode(), signature, secret)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid signature")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")
    event = data.get("event", "")
    entity = (((data.get("payload") or {}).get("subscription") or {}).get("entity") or {})
    sub_id = entity.get("id")
    if not sub_id:
        return {"status": "ignored"}
    user = await db.users.find_one({"subscriptionId": sub_id})
    if not user:
        return {"status": "ignored"}
    active_events = ("subscription.activated", "subscription.charged", "subscription.resumed", "subscription.authenticated")
    inactive_events = ("subscription.halted", "subscription.cancelled", "subscription.completed", "subscription.paused")
    new_status = "active" if event in active_events else ("inactive" if event in inactive_events else None)
    if new_status:
        await db.users.update_one({"user_id": user["user_id"]},
                                  {"$set": {"subscriptionStatus": new_status, "subscriptionEvent": event}})
    return {"status": "ok", "event": event}


@api.post("/subscription/simulate")
async def subscription_simulate(body: SubSimIn, user=Depends(get_current_user)):
    """TEST-ONLY: simulate the subscription webhook outcome without a real charge."""
    if body.status not in ("active", "inactive"):
        raise HTTPException(status_code=400, detail="status must be active or inactive")
    await db.users.update_one({"user_id": user["user_id"]},
                              {"$set": {"subscriptionStatus": body.status}})
    return {"subscriptionStatus": body.status}


@api.get("/")
async def root():
    return {"service": "Peddle Cart API", "status": "ok"}


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================= Startup: indexes + seed =======================
async def seed():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.stores.create_index("slug", unique=True)
    await db.products.create_index("storeSlug")
    await db.orders.create_index("order_id", unique=True)
    await db.orders.create_index("razorpayOrderId")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.user_sessions.create_index("session_token")
    await db.seller_routes.create_index("sellerId", unique=True)
    await db.files.create_index("storage_path")
    await db.pending_otps.create_index("otp_id", unique=True)
    await db.pending_otps.create_index("expires_at", expireAfterSeconds=0)

    async def ensure_seller(email, password, name, slug, store_name):
        u = await db.users.find_one({"email": email})
        if not u:
            uid = new_id("user")
            u = {"user_id": uid, "email": email, "name": name,
                 "password_hash": security.hash_password(password), "role": "seller",
                 "authProvider": "password", "subscriptionStatus": "inactive",
                 "created_at": iso(now())}
            await db.users.insert_one(u)
        s = await db.stores.find_one({"sellerId": u["user_id"]})
        if not s and not await db.stores.find_one({"slug": slug}):
            await db.stores.insert_one({"store_id": new_id("store"), "sellerId": u["user_id"],
                                        "name": store_name, "slug": slug,
                                        "acceptanceWindowMinutes": DEFAULT_WINDOW_MIN,
                                        "created_at": iso(now())})
        return u

    owner = await ensure_seller(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"],
                                "Marketo Owner", "demo-store", "Demo Store")
    await ensure_seller("seller2@marketo-demo.com", "Seller2@2026", "Artisan Seller",
                        "artisan-shop", "Artisan Shop")
    await db.stores.update_one({"slug": "demo-store", "bio": {"$exists": False}},
                               {"$set": {"bio": "Small-batch pantry goods and everyday basics, packed and shipped by hand."}})
    await db.stores.update_one({"slug": "artisan-shop", "bio": {"$exists": False}},
                               {"$set": {"bio": "Handmade ceramics and textiles from a tiny home studio."}})

    if await db.products.count_documents({"storeSlug": "demo-store"}) == 0:
        await db.products.insert_many([
            {"product_id": new_id("prod"), "sellerId": owner["user_id"], "storeSlug": "demo-store",
             "title": "Organic Honey (500g)", "description": "Raw wildflower honey",
             "price": 350.0, "stock": 40, "optionGroups": [], "active": True,
             "image": None, "created_at": iso(now())},
            {"product_id": new_id("prod"), "sellerId": owner["user_id"], "storeSlug": "demo-store",
             "title": "Cotton T-Shirt", "description": "Handmade, soft cotton",
             "price": 600.0, "stock": None, "active": True, "image": None,
             "optionGroups": [{"name": "Size", "options": [
                 {"label": "S", "priceDelta": 0, "stock": 10},
                 {"label": "M", "priceDelta": 0, "stock": 15},
                 {"label": "L", "priceDelta": 50, "stock": 8}]}],
             "created_at": iso(now())},
        ])


@app.on_event("startup")
async def on_startup():
    try:
        await asyncio.to_thread(storage.init_storage)
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"storage init failed: {e}")
    try:
        await seed()
        logger.info("Marketo startup seed complete")
    except Exception as e:
        logger.error(f"seed error: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
