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


def _default_sqlite_path() -> Path:
    override = os.environ.get("STALLWISE_SQLITE_PATH")
    if override:
        return Path(override)
    return Path("/data/stallwise.db") if Path("/data").is_dir() else (ROOT_DIR / "stallwise.db")


DB_FILE = _default_sqlite_path()


# Container filesystems are ephemeral. If we are running on a hosting platform
# and writing SQLite to a path that is not a mounted volume, every restart or
# redeploy silently rolls the data back to whatever shipped in the image —
# sellers lose their products and their shops go empty with no error anywhere.
_PLATFORM_ENV_VARS = (
    "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID",
    "RENDER", "FLY_APP_NAME", "DYNO", "KUBERNETES_SERVICE_HOST",
)
# Paths a hosting provider gives you for a persistent volume.
_VOLUME_PREFIXES = ("/data", "/mnt", "/var/lib/stallwise", "/storage")


def on_hosting_platform() -> bool:
    return any(os.environ.get(v) for v in _PLATFORM_ENV_VARS)


def ephemeral_storage_warning() -> Optional[str]:
    """Return a message when writes are not landing somewhere durable.

    Keyed off the engine actually in use, not off whether DATABASE_URL is set —
    a configured-but-unreachable Postgres is the case that most needs saying,
    and checking the config instead of the engine would hide exactly that.
    """
    if _ENGINE == "postgres" and _pool:
        return None  # Durable.

    path = str(DB_FILE.resolve()) if hasattr(DB_FILE, "resolve") else str(DB_FILE)
    durable_path = any(path == p or path.startswith(p.rstrip("/") + "/")
                       for p in _VOLUME_PREFIXES)

    if get_database_url():
        return (
            "DATABASE_URL is configured but Postgres is NOT in use — the app fell "
            f"back to SQLite at {path}, so writes are going to the wrong database"
            + ("" if durable_path else " and will be lost on the next restart")
            + ". Check the startup log for the connection error."
            + (f" Last error: {_last_db_error}" if _last_db_error else "")
        )

    if not on_hosting_platform() or durable_path:
        return None  # Local development, or a mounted volume.

    return (
        f"Data written to {path} will be LOST on the next restart or deploy — "
        "this path is inside the container, not a mounted volume. Set DATABASE_URL "
        "to a PostgreSQL instance, or mount a volume at /data."
    )


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
        delivery_fee NUMERIC DEFAULT 0,
    free_delivery_above NUMERIC,
    dispatch_days INT DEFAULT 2,
    gstin TEXT,
    hsn_code TEXT,
    notify_new_order BOOLEAN DEFAULT 1,
    notify_daily_summary BOOLEAN DEFAULT 0,
    notify_weekly_digest BOOLEAN DEFAULT 0,
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
        slug TEXT,
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
    -- The payment webhook looks an order up by this on every payment.
    CREATE INDEX IF NOT EXISTS idx_orders_rp_order ON orders(razorpay_order_id);

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

    CREATE TABLE IF NOT EXISTS platform_plans (
        interval TEXT PRIMARY KEY,
        amount NUMERIC NOT NULL,
        plan_id TEXT NOT NULL
    );

    -- Product photos live here, not on disk. The container filesystem is
    -- rebuilt on every deploy and `uploads` is in .dockerignore, so a seller
    -- who listed twenty products with photos came back the next day to twenty
    -- broken images. Bytes in the database survive a restart; nothing else
    -- available to us does without the seller configuring object storage.
    CREATE TABLE IF NOT EXISTS media (
        path TEXT PRIMARY KEY,
        owner_id TEXT,
        content_type TEXT NOT NULL,
        bytes BLOB NOT NULL,
        size INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    _sqlite_migrate(c)
    conn.commit()


# PostgreSQL schema. `_init_sqlite_schema` only ever created SQLite tables, and
# `_pg_migrate` only ever ran ALTER/CREATE INDEX — so a fresh Postgres database
# had NO tables. The app connected, logged a few warnings, then failed every
# query and silently fell back to SQLite. This is the missing half.
_PG_SCHEMA = """
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
    delivery_fee NUMERIC DEFAULT 0,
    free_delivery_above NUMERIC,
    dispatch_days INT DEFAULT 2,
    gstin TEXT,
    hsn_code TEXT,
    notify_new_order BOOLEAN DEFAULT TRUE,
    notify_daily_summary BOOLEAN DEFAULT FALSE,
    notify_weekly_digest BOOLEAN DEFAULT FALSE,
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
    active BOOLEAN DEFAULT TRUE,
    image TEXT,
    images TEXT DEFAULT '[]',
    payment_methods TEXT DEFAULT '["online"]',
    slug TEXT,
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
    mock_payment BOOLEAN DEFAULT FALSE,
    otp_code_hash TEXT,
    otp_enc TEXT,
    otp_attempts INT DEFAULT 0,
    otp_locked BOOLEAN DEFAULT FALSE,
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
-- The payment webhook looks an order up by this on every payment.
CREATE INDEX IF NOT EXISTS idx_orders_rp_order ON orders(razorpay_order_id);

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

CREATE TABLE IF NOT EXISTS platform_plans (
    interval TEXT PRIMARY KEY,
    amount NUMERIC NOT NULL,
    plan_id TEXT NOT NULL
);

-- See the note on the SQLite copy: product photos are stored here because the
-- container filesystem does not survive a deploy.
CREATE TABLE IF NOT EXISTS media (
    path TEXT PRIMARY KEY,
    owner_id TEXT,
    content_type TEXT NOT NULL,
    bytes BYTEA NOT NULL,
    size INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


# Additive column migrations for databases created by an older schema version.
_COLUMN_MIGRATIONS: Dict[str, Dict[str, str]] = {
    "seller_routes": {
        "product_config_id": "TEXT",
        "settlement_status": "TEXT",
    },
    "products": {
        "images": "TEXT DEFAULT '[]'",
        "payment_methods": "TEXT DEFAULT '[\"online\"]'",
        "slug": "TEXT",
    },
    "orders": {
        "window_expires_at": "TEXT",
        "dispute_reason": "TEXT",
        "payment_method": "TEXT DEFAULT 'online'",
    },
    "stores": {
        "delivery_fee": "NUMERIC DEFAULT 0",
        "free_delivery_above": "NUMERIC",
        "dispatch_days": "INT DEFAULT 2",
        "gstin": "TEXT",
        "hsn_code": "TEXT",
        "notify_new_order": "BOOLEAN DEFAULT TRUE",
        "notify_daily_summary": "BOOLEAN DEFAULT FALSE",
        "notify_weekly_digest": "BOOLEAN DEFAULT FALSE",
    },
}


# Indexes that depend on migrated columns, so they run after the ALTERs.
_POST_MIGRATION_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_store_slug ON products(store_slug, slug)",
]


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
    for stmt in _POST_MIGRATION_INDEXES:
        try:
            c.execute(stmt)
        except Exception as e:
            logger.warning(f"sqlite index: {e}")


async def _pg_migrate(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        # Tables first — everything below assumes they exist. Idempotent, so
        # this is safe against a database that is already populated.
        async with conn.transaction():
            await conn.execute(_PG_SCHEMA)
        for table, cols in _COLUMN_MIGRATIONS.items():
            for name, ddl in cols.items():
                try:
                    await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}")
                except Exception as e:
                    logger.warning(f"pg migrate {table}.{name}: {e}")
        for stmt in _POST_MIGRATION_INDEXES:
            try:
                await conn.execute(stmt)
            except Exception as e:
                logger.warning(f"pg index: {e}")


def _get_sqlite_conn() -> sqlite3.Connection:
    global _sqlite_conn
    if _sqlite_conn is None:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _sqlite_conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
        _init_sqlite_schema(_sqlite_conn)
    return _sqlite_conn


def encode_args(args: tuple) -> tuple:
    """JSON-encode dict/list parameters.

    The JSON-ish columns (option_groups, images, payment_methods, address,
    items) are declared TEXT on both engines, so a Python list has to be
    serialised before it is bound. This ran on the SQLite path only, which is
    why every product INSERT failed against Postgres with

        DataError: invalid input for query argument $8: [] (expected str, got list)

    No query in this codebase binds a native Postgres array, so encoding here is
    unconditional. If one ever does, it must bypass this.
    """
    return tuple(json.dumps(a) if isinstance(a, (dict, list)) else a for a in args)


def _pg_to_sqlite(query: str, args: tuple):
    q = re.sub(r"::jsonb?", "", query)
    q = re.sub(r"\$\d+", "?", q)
    return q, encode_args(args)


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
    warning = ephemeral_storage_warning()
    if warning:
        # Loud on purpose: the failure is otherwise completely silent — the app
        # serves 200s and simply forgets everything it was told.
        logger.critical("=" * 78)
        logger.critical("EPHEMERAL DATABASE: %s", warning)
        logger.critical("=" * 78)
    else:
        logger.info(f"SQLite database active and ready at {DB_FILE}")
    return None


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute query and return single row as dict, or None."""
    global _ENGINE, _pool
    if _ENGINE == "postgres" and _pool:
        try:
            async with _pool.acquire() as conn:
                record = await conn.fetchrow(query, *encode_args(args))
                return dict(record) if record else None
        except Exception as e:
            # Deliberately NOT falling back to SQLite. Serving one query from a
            # different database than the last is how published products
            # vanished: the INSERT went to SQLite, every read went to Postgres.
            # A failed query must fail loudly, not quietly write elsewhere.
            logger.error(f"Postgres fetch_one failed: {e}")
            raise

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
                records = await conn.fetch(query, *encode_args(args))
                return [dict(r) for r in records]
        except Exception as e:
            # Deliberately NOT falling back to SQLite. Serving one query from a
            # different database than the last is how published products
            # vanished: the INSERT went to SQLite, every read went to Postgres.
            # A failed query must fail loudly, not quietly write elsewhere.
            logger.error(f"Postgres fetch_all failed: {e}")
            raise

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
                return await conn.fetchval(query, *encode_args(args))
        except Exception as e:
            # Deliberately NOT falling back to SQLite. Serving one query from a
            # different database than the last is how published products
            # vanished: the INSERT went to SQLite, every read went to Postgres.
            # A failed query must fail loudly, not quietly write elsewhere.
            logger.error(f"Postgres fetch_val failed: {e}")
            raise

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
                return await conn.execute(query, *encode_args(args))
        except Exception as e:
            # Deliberately NOT falling back to SQLite. Serving one query from a
            # different database than the last is how published products
            # vanished: the INSERT went to SQLite, every read went to Postgres.
            # A failed query must fail loudly, not quietly write elsewhere.
            logger.error(f"Postgres execute failed: {e}")
            raise

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
