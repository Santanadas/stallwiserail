"""High-reliability database engine with dual PostgreSQL and SQLite fallback support.
Supports PostgreSQL (Supabase, Railway, Neon) and automatically falls back to
high-durability WAL SQLite if PostgreSQL is unreachable or unconfigured.
"""
import os
import re
import sys
import json
import sqlite3
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, unquote

import asyncpg

logger = logging.getLogger("stallwise.db")

_ENGINE: str = "sqlite" # "postgres" | "sqlite"
_pool: Optional[asyncpg.Pool] = None
_sqlite_conn: Optional[sqlite3.Connection] = None
_sqlite_lock = asyncio.Lock()
_last_db_error: Optional[str] = None

ROOT_DIR = Path(__file__).parent.resolve()
DB_FILE = Path("/data/stallwise.db") if Path("/data").is_dir() else (ROOT_DIR / "stallwise.db")


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
    """Register JSON/JSONB encoders and decoders on PostgreSQL pool connections."""
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


def _init_sqlite_schema(conn: sqlite3.Connection):
    """Initialize all SQLite tables, indexes and settings."""
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.execute("PRAGMA foreign_keys=ON;")

    c.executescript("""
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
        name TEXT,
        password_hash TEXT,
        otp_hash TEXT NOT NULL,
        purpose TEXT NOT NULL,
        attempts INT DEFAULT 0,
        locked BOOLEAN DEFAULT 0,
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
        used BOOLEAN DEFAULT 0
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
        option_groups TEXT DEFAULT '[]',
        active BOOLEAN DEFAULT 1,
        image TEXT,
        images TEXT DEFAULT '[]',
        payment_methods TEXT DEFAULT '["online"]',
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
        address TEXT DEFAULT '{}',
        items TEXT DEFAULT '[]',
        subtotal NUMERIC NOT NULL,
        delivery_fee NUMERIC DEFAULT 0,
        tax NUMERIC DEFAULT 0,
        amount NUMERIC NOT NULL,
        status TEXT NOT NULL,
        razorpay_order_id TEXT,
        razorpay_payment_id TEXT,
        razorpay_key_id TEXT,
        mock_payment BOOLEAN DEFAULT 0,
        otp_code_hash TEXT,
        otp_enc TEXT,
        otp_attempts INT DEFAULT 0,
        otp_locked BOOLEAN DEFAULT 0,
        otp_generated_at TEXT,
        shipped_at TEXT,
        paid_at TEXT,
        delivered_at TEXT,
        window_expires_at TEXT,
        dispute_reason TEXT,
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
        product_config_id TEXT,
        settlement_status TEXT,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS seller_gateways (
        seller_id TEXT PRIMARY KEY,
        key_id TEXT NOT NULL,
        key_secret_enc TEXT NOT NULL,
        webhook_secret_enc TEXT,
        enabled BOOLEAN DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS platform_plans (
        interval TEXT PRIMARY KEY,
        amount NUMERIC NOT NULL,
        plan_id TEXT NOT NULL
    );
    """)
    _sqlite_migrate(c)
    conn.commit()


# Additive column migrations for databases created by an older schema version.
_COLUMN_MIGRATIONS: Dict[str, Dict[str, str]] = {
    "seller_routes": {
        "product_config_id": "TEXT",
        "settlement_status": "TEXT",
    },
    "products": {
        "images": "TEXT DEFAULT '[]'",
        "payment_methods": "TEXT DEFAULT '[\"online\"]'",
    },
    "orders": {
        "window_expires_at": "TEXT",
        "dispute_reason": "TEXT",
        "payment_method": "TEXT DEFAULT 'online'",
    },
}


def _sqlite_migrate(c: sqlite3.Cursor):
    for table, cols in _COLUMN_MIGRATIONS.items():
        try:
            existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()}
        except Exception:
            continue
        for name, ddl in cols.items():
            if name not in existing:
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                except Exception as e:
                    logger.warning(f"sqlite migrate {table}.{name}: {e}")


async def _pg_migrate(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        for table, cols in _COLUMN_MIGRATIONS.items():
            for name, ddl in cols.items():
                try:
                    await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}")
                except Exception as e:
                    logger.warning(f"pg migrate {table}.{name}: {e}")


def _get_sqlite_conn() -> sqlite3.Connection:
    global _sqlite_conn
    if _sqlite_conn is None:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _sqlite_conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
        _init_sqlite_schema(_sqlite_conn)
    return _sqlite_conn


def _pg_to_sqlite(query: str, args: tuple):
    q = re.sub(r"::jsonb?", "", query)
    q = re.sub(r"\$\d+", "?", q)
    formatted_args = []
    for a in args:
        if isinstance(a, (dict, list)):
            formatted_args.append(json.dumps(a))
        else:
            formatted_args.append(a)
    return q, tuple(formatted_args)


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    d = dict(row)
    for k in ("option_groups", "images", "payment_methods", "address", "items", "notes"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                pass
    return d


async def init_db():
    """Initialize database connection. Tries PostgreSQL; falls back to SQLite."""
    global _pool, _ENGINE, _last_db_error
    db_url = get_database_url()

    if db_url:
        try:
            parsed = urlparse(db_url)
            username = unquote(parsed.username) if parsed.username else None
            password = unquote(parsed.password) if parsed.password else None
            hostname = parsed.hostname
            port = parsed.port or 5432
            dbname = (parsed.path or "/postgres").lstrip("/") or "postgres"

            ssl_mode = None
            if any(k in db_url.lower() for k in ("supabase", "pooler", "railway", "render", "neon", "sslmode=require", "aws", ".com", ".co", ".net")):
                ssl_mode = "require"

            if hostname and username and password and not any(k in password for k in ("[YOUR-", "YOUR-PASSWORD")):
                pool = await asyncpg.create_pool(
                    user=username,
                    password=password,
                    host=hostname,
                    port=port,
                    database=dbname,
                    init=_init_connection,
                    min_size=1,
                    max_size=10,
                    ssl=ssl_mode,
                    statement_cache_size=0,
                    timeout=5.0,
                )
                # Verify connection
                async with pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                
                _pool = pool
                _ENGINE = "postgres"
                await _pg_migrate(pool)
                logger.info(f"Connected to PostgreSQL database at {hostname}")
                return _pool
        except Exception as e:
            logger.warning(f"PostgreSQL connection attempt failed ({e}). Activating high-reliability local SQLite engine.")
            _last_db_error = str(e)
            _pool = None

    # Fallback to persistent SQLite
    _ENGINE = "sqlite"
    await asyncio.to_thread(_get_sqlite_conn)
    logger.info(f"SQLite database active and ready at {DB_FILE}")
    return None


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute query and return single row as dict, or None."""
    global _ENGINE, _pool
    if _ENGINE == "postgres" and _pool:
        try:
            async with _pool.acquire() as conn:
                record = await conn.fetchrow(query, *args)
                return dict(record) if record else None
        except Exception as e:
            logger.error(f"Postgres fetch_one error: {e}. Falling back to SQLite.")

    # SQLite execution
    def _run():
        conn = _get_sqlite_conn()
        q, a = _pg_to_sqlite(query, args)
        cur = conn.cursor()
        cur.execute(q, a)
        row = cur.fetchone()
        return _row_to_dict(row)

    async with _sqlite_lock:
        return await asyncio.to_thread(_run)


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Execute query and return all matching rows as dicts."""
    global _ENGINE, _pool
    if _ENGINE == "postgres" and _pool:
        try:
            async with _pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                return [dict(r) for r in records]
        except Exception as e:
            logger.error(f"Postgres fetch_all error: {e}. Falling back to SQLite.")

    # SQLite execution
    def _run():
        conn = _get_sqlite_conn()
        q, a = _pg_to_sqlite(query, args)
        cur = conn.cursor()
        cur.execute(q, a)
        rows = cur.fetchall()
        return [_row_to_dict(r) for r in rows]

    async with _sqlite_lock:
        return await asyncio.to_thread(_run)


async def fetch_val(query: str, *args) -> Any:
    """Execute query and return single scalar value."""
    global _ENGINE, _pool
    if _ENGINE == "postgres" and _pool:
        try:
            async with _pool.acquire() as conn:
                return await conn.fetchval(query, *args)
        except Exception as e:
            logger.error(f"Postgres fetch_val error: {e}. Falling back to SQLite.")

    # SQLite execution
    def _run():
        conn = _get_sqlite_conn()
        q, a = _pg_to_sqlite(query, args)
        cur = conn.cursor()
        cur.execute(q, a)
        row = cur.fetchone()
        return row[0] if row else None

    async with _sqlite_lock:
        return await asyncio.to_thread(_run)


async def execute(query: str, *args) -> str:
    """Execute query (INSERT, UPDATE, DELETE) and return status."""
    global _ENGINE, _pool
    if _ENGINE == "postgres" and _pool:
        try:
            async with _pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Postgres execute error: {e}. Falling back to SQLite.")

    # SQLite execution
    def _run():
        conn = _get_sqlite_conn()
        q, a = _pg_to_sqlite(query, args)
        with conn:
            cur = conn.cursor()
            cur.execute(q, a)
        return "SUCCESS"

    async with _sqlite_lock:
        return await asyncio.to_thread(_run)


async def close_db():
    global _pool, _sqlite_conn
    if _pool:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
    if _sqlite_conn:
        try:
            _sqlite_conn.close()
        except Exception:
            pass
        _sqlite_conn = None
