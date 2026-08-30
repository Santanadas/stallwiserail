"""PostgreSQL database engine and asyncpg connection pool for Stall Wise.
Supports Supabase, Railway Postgres, Neon, and self-hosted PostgreSQL.
"""
import os
import json
import logging
import asyncio
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import asyncpg
from fastapi import HTTPException

logger = logging.getLogger("stallwise.db")

_pool: Optional[asyncpg.Pool] = None
_last_db_error: Optional[str] = None


def get_database_url() -> str:
    url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("SUPABASE_DB_URL")
        or os.environ.get("PGDATABASE_URL")
        or os.environ.get("POSTGRESQL_URL")
        or ""
    ).strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


async def _init_connection(conn: asyncpg.Connection):
    """Register JSON/JSONB encoders and decoders on every pool connection."""
    try:
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
        await conn.set_type_codec(
            "json",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
    except Exception as e:
        logger.debug(f"JSON codec init notice: {e}")


async def init_db() -> Optional[asyncpg.Pool]:
    """Initialize asyncpg pool and automatically create all tables and indexes."""
    global _pool, _last_db_error
    db_url = get_database_url()

    if not db_url:
        _last_db_error = "DATABASE_URL environment variable is missing or empty."
        logger.warning(_last_db_error)
        _pool = None
        return None

    # Determine SSL mode for remote cloud databases (Supabase, Railway, Neon, AWS)
    ssl_context = None
    if any(k in db_url.lower() for k in ("supabase", "pooler", "railway", "render", "neon", "sslmode=require", "aws")):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    # Clean URL of query parameters if asyncpg doesn't parse them natively
    clean_url = db_url.split("?")[0] if "?" in db_url else db_url

    try:
        # statement_cache_size=0 is required for Supabase Transaction Poolers (pgBouncer)
        if ssl_context:
            _pool = await asyncpg.create_pool(
                clean_url,
                init=_init_connection,
                min_size=1,
                max_size=10,
                ssl=ssl_context,
                statement_cache_size=0,
                timeout=10.0,
            )
        else:
            _pool = await asyncpg.create_pool(
                clean_url,
                init=_init_connection,
                min_size=1,
                max_size=10,
                statement_cache_size=0,
                timeout=10.0,
            )
        logger.info("Connected to PostgreSQL database pool successfully")
        _last_db_error = None

        # Create tables and indexes safely
        async with _pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                password_hash TEXT,
                role TEXT DEFAULT 'seller',
                auth_provider TEXT DEFAULT 'password',
                subscription_status TEXT DEFAULT 'inactive',
                subscription_id TEXT,
                subscription_interval TEXT,
                subscription_expires_at TEXT,
                picture TEXT,
                avatar TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

            CREATE TABLE IF NOT EXISTS pending_otps (
                otp_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                email TEXT NOT NULL,
                otp_hash TEXT NOT NULL,
                purpose TEXT NOT NULL,
                attempts INT DEFAULT 0,
                locked BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_pending_otps_user ON pending_otps(user_id);
            CREATE INDEX IF NOT EXISTS idx_pending_otps_email ON pending_otps(email);

            CREATE TABLE IF NOT EXISTS login_attempts (
                identifier TEXT PRIMARY KEY,
                count INT DEFAULT 0,
                locked_until TEXT
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);

            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                bio TEXT,
                logo TEXT,
                acceptance_window_minutes INT DEFAULT 120,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_stores_seller ON stores(seller_id);
            CREATE INDEX IF NOT EXISTS idx_stores_slug ON stores(slug);

            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                store_slug TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                price NUMERIC NOT NULL,
                stock INT,
                option_groups JSONB DEFAULT '[]'::jsonb,
                active BOOLEAN DEFAULT TRUE,
                image TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_products_seller ON products(seller_id);
            CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_slug);

            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                store_slug TEXT NOT NULL,
                buyer_name TEXT NOT NULL,
                buyer_email TEXT NOT NULL,
                buyer_phone TEXT NOT NULL,
                address JSONB DEFAULT '{}'::jsonb,
                items JSONB DEFAULT '[]'::jsonb,
                subtotal NUMERIC NOT NULL,
                delivery_fee NUMERIC DEFAULT 0,
                tax NUMERIC DEFAULT 0,
                amount NUMERIC NOT NULL,
                status TEXT NOT NULL,
                razorpay_order_id TEXT,
                razorpay_payment_id TEXT,
                razorpay_key_id TEXT,
                mock_payment BOOLEAN DEFAULT FALSE,
                otp_code_hash TEXT,
                otp_enc TEXT,
                otp_attempts INT DEFAULT 0,
                otp_locked BOOLEAN DEFAULT FALSE,
                otp_generated_at TEXT,
                shipped_at TEXT,
                paid_at TEXT,
                delivered_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_orders_seller ON orders(seller_id);
            CREATE INDEX IF NOT EXISTS idx_orders_store ON orders(store_slug);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

            CREATE TABLE IF NOT EXISTS seller_routes (
                seller_id TEXT PRIMARY KEY,
                store_slug TEXT NOT NULL,
                account_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                legal_business_name TEXT,
                contact_name TEXT,
                phone TEXT,
                beneficiary_name TEXT,
                account_number_enc TEXT,
                account_number_last4 TEXT,
                ifsc TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS seller_gateways (
                seller_id TEXT PRIMARY KEY,
                key_id TEXT NOT NULL,
                key_secret_enc TEXT NOT NULL,
                webhook_secret_enc TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS platform_plans (
                interval TEXT PRIMARY KEY,
                amount NUMERIC NOT NULL,
                plan_id TEXT NOT NULL
            );
            """)
            logger.info("PostgreSQL database tables and indexes verified successfully")
    except Exception as e:
        _last_db_error = str(e)
        logger.error(f"PostgreSQL connection error: {e}")
        _pool = None
        return None

    return _pool


async def close_db():
    global _pool
    if _pool:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool, _last_db_error
    if _pool is None:
        await init_db()
    if _pool is None:
        err_msg = _last_db_error or "DATABASE_URL is not set or unreachable"
        raise HTTPException(
            status_code=503,
            detail=f"Database connection error: {err_msg}. Please verify your DATABASE_URL in Railway variables."
        )
    return _pool


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute query and return single row as dict, or None."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow(query, *args)
        return dict(record) if record else None


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Execute query and return all matching rows as dicts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        records = await conn.fetch(query, *args)
        return [dict(r) for r in records]


async def fetch_val(query: str, *args) -> Any:
    """Execute query and return single scalar value."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args) -> str:
    """Execute query (INSERT, UPDATE, DELETE) and return status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)
