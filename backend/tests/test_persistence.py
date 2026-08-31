"""Guards against the failure that wiped a live catalogue.

backend/stallwise.db was tracked in git, so `COPY . .` baked it into the Docker
image. With no DATABASE_URL and no mounted volume, the app wrote SQLite inside
the container — and every restart restored the image's copy over it. Sellers
published products, the container bounced, and their shops went empty with no
error logged anywhere.

These cover the two things that make that impossible to repeat silently: the
warning, and /health reporting it.
"""
from pathlib import Path

import db


def _clear_platform(monkeypatch):
    for var in db._PLATFORM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    for var in ("DATABASE_URL", "POSTGRES_URL", "SUPABASE_DB_URL",
                "PGDATABASE_URL", "POSTGRESQL_URL"):
        monkeypatch.delenv(var, raising=False)


def test_no_warning_for_local_development(monkeypatch):
    _clear_platform(monkeypatch)
    monkeypatch.setattr(db, "DB_FILE", Path("/home/dev/app/backend/stallwise.db"))
    assert db.ephemeral_storage_warning() is None


def test_warns_when_hosted_and_writing_inside_the_container(monkeypatch):
    _clear_platform(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setattr(db, "DB_FILE", Path("/app/backend/stallwise.db"))

    warning = db.ephemeral_storage_warning()
    assert warning and "LOST" in warning
    assert "/app/backend/stallwise.db" in warning


def test_no_warning_when_the_file_is_on_a_mounted_volume(monkeypatch):
    _clear_platform(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setattr(db, "DB_FILE", Path("/data/stallwise.db"))
    assert db.ephemeral_storage_warning() is None


def test_no_warning_when_postgres_is_actually_in_use(monkeypatch):
    _clear_platform(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    monkeypatch.setattr(db, "_ENGINE", "postgres")
    monkeypatch.setattr(db, "_pool", object())
    monkeypatch.setattr(db, "DB_FILE", Path("/app/backend/stallwise.db"))
    assert db.ephemeral_storage_warning() is None


def test_warns_loudly_when_postgres_is_configured_but_not_in_use(monkeypatch):
    """The case that hid the bug: Supabase is wired up, the app fell back to
    SQLite anyway, and nothing said so."""
    _clear_platform(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@host/db")
    monkeypatch.setattr(db, "_ENGINE", "sqlite")
    monkeypatch.setattr(db, "_pool", None)
    monkeypatch.setattr(db, "_last_db_error", "connection timed out")
    monkeypatch.setattr(db, "DB_FILE", Path("/app/backend/stallwise.db"))

    warning = db.ephemeral_storage_warning()
    assert warning
    assert "Postgres is NOT in use" in warning
    assert "connection timed out" in warning


def test_a_volume_lookalike_path_still_warns(monkeypatch):
    # /database is not /data — a prefix check must not be fooled by it.
    _clear_platform(monkeypatch)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setattr(db, "DB_FILE", Path("/database/stallwise.db"))
    assert db.ephemeral_storage_warning() is not None


# --- /health surfaces it without needing shell access ---------------------
def test_health_reports_no_storage_warning_on_a_normal_boot(app_client):
    # conftest deliberately unsets BREVO_API_KEY, so the suite runs "degraded"
    # on config. What matters here is that storage is not flagged.
    body = app_client.get("/health").json()
    assert "warning" not in body
    assert body["engine"] in ("sqlite", "postgres")


def test_health_reports_degraded_storage(app_client, monkeypatch):
    monkeypatch.setattr(db, "ephemeral_storage_warning", lambda: "Data will be LOST.")
    body = app_client.get("/health").json()
    assert body["status"] != "ok"
    assert body["warning"] == "Data will be LOST."


def test_health_names_the_missing_environment_variables(app_client, monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    body = app_client.get("/health").json()
    assert body["status"] != "ok"
    assert "RAZORPAY_KEY_ID" in body["missingConfig"]
    # The ones that are set must not be reported.
    assert "ENCRYPTION_KEY" not in body["missingConfig"]


def test_health_shouts_when_the_otp_debug_echo_is_on(app_client, monkeypatch):
    """DEV_OTP_ECHO returns login OTPs in API responses. On a public deploy
    that is a complete authentication bypass — it must outrank every other
    warning so it cannot be missed."""
    monkeypatch.setenv("DEV_OTP_ECHO", "true")
    body = app_client.get("/health").json()
    assert body["status"] == "insecure"
    assert "DEV_OTP_ECHO" in body["danger"]


def test_health_is_quiet_about_otp_echo_when_it_is_off(app_client, monkeypatch):
    monkeypatch.delenv("DEV_OTP_ECHO", raising=False)
    body = app_client.get("/health").json()
    assert body["status"] != "insecure"
    assert "danger" not in body



# --- A failed Postgres query must never be re-run against SQLite ----------
class _BrokenPool:
    """A pool whose every acquire() raises, like an unreachable Supabase."""
    def acquire(self):
        raise ConnectionError("connection to server failed")


def _use_broken_postgres(monkeypatch):
    monkeypatch.setattr(db, "_ENGINE", "postgres")
    monkeypatch.setattr(db, "_pool", _BrokenPool())


def test_a_failed_write_is_not_diverted_into_sqlite(app_client, monkeypatch):
    """The bug: an INSERT that failed on Postgres silently landed in SQLite,
    so the row was invisible to every later Postgres read and gone at restart.
    It must raise instead."""
    import asyncio

    import pytest

    _use_broken_postgres(monkeypatch)
    with pytest.raises(ConnectionError):
        asyncio.run(db.execute("INSERT INTO products (product_id) VALUES ($1)", "p1"))


def test_failed_reads_raise_rather_than_return_stale_sqlite_rows(app_client, monkeypatch):
    import asyncio

    import pytest

    _use_broken_postgres(monkeypatch)
    for call in (
        lambda: db.fetch_one("SELECT 1"),
        lambda: db.fetch_all("SELECT 1"),
        lambda: db.fetch_val("SELECT 1"),
    ):
        with pytest.raises(ConnectionError):
            asyncio.run(call())


# --- The Postgres schema must actually create the tables ------------------
def test_pg_schema_creates_every_table_the_sqlite_schema_does():
    import re

    sqlite_src = db._init_sqlite_schema.__doc__ or ""
    import inspect
    sqlite_body = inspect.getsource(db._init_sqlite_schema)
    sqlite_tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sqlite_body))
    pg_tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", db._PG_SCHEMA))
    assert sqlite_tables, "sanity: found no tables in the SQLite schema"
    assert sqlite_tables == pg_tables, (
        f"Postgres schema is missing: {sorted(sqlite_tables - pg_tables)}"
    )


def test_pg_schema_uses_postgres_boolean_literals():
    # `BOOLEAN DEFAULT 0` is valid SQLite and a type error in Postgres.
    assert "BOOLEAN DEFAULT 0" not in db._PG_SCHEMA
    assert "BOOLEAN DEFAULT 1" not in db._PG_SCHEMA
    assert "BOOLEAN DEFAULT TRUE" in db._PG_SCHEMA
    assert "BOOLEAN DEFAULT FALSE" in db._PG_SCHEMA


# --- JSON columns must be serialised on BOTH engines ----------------------
def test_encode_args_serialises_lists_and_dicts():
    out = db.encode_args(("prod_1", [], {"a": 1}, [{"name": "Size"}], 599, None, True))
    assert out == ("prod_1", "[]", '{"a": 1}', '[{"name": "Size"}]', 599, None, True)


def test_sqlite_path_still_encodes():
    q, a = db._pg_to_sqlite("INSERT INTO products VALUES ($1, $2)", ("p1", ["online"]))
    assert q == "INSERT INTO products VALUES (?, ?)"
    assert a == ("p1", '["online"]')


class _RecordingConn:
    """Captures what actually reaches asyncpg."""
    last_args = None

    async def fetchrow(self, q, *a):
        _RecordingConn.last_args = a
        return None

    async def fetch(self, q, *a):
        _RecordingConn.last_args = a
        return []

    async def fetchval(self, q, *a):
        _RecordingConn.last_args = a
        return None

    async def execute(self, q, *a):
        _RecordingConn.last_args = a
        return "INSERT 0 1"


class _RecordingPool:
    def acquire(self):
        conn = _RecordingConn()

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *e):
                return False

        return _Ctx()


def test_postgres_path_encodes_json_columns_too(monkeypatch):
    """The production bug: only the SQLite path serialised lists, so every
    product INSERT raised
        DataError: invalid input for query argument $8: [] (expected str, got list)
    against Postgres — and the old fallback then wrote it to SQLite instead."""
    import asyncio

    monkeypatch.setattr(db, "_ENGINE", "postgres")
    monkeypatch.setattr(db, "_pool", _RecordingPool())

    payload = ("prod_1", [], ["online", "cod"], [{"name": "Size", "options": []}])
    for call in (db.execute, db.fetch_one, db.fetch_all, db.fetch_val):
        _RecordingConn.last_args = None
        asyncio.run(call("INSERT INTO products VALUES ($1,$2,$3,$4)", *payload))
        got = _RecordingConn.last_args
        assert got is not None, call.__name__
        assert all(not isinstance(x, (list, dict)) for x in got), (
            f"{call.__name__} passed a raw Python container to asyncpg: {got}"
        )
        assert got[1] == "[]" and got[2] == '["online", "cod"]'
