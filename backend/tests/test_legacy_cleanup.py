"""Removing a feature has to remove what it stored.

seller_gateways held sellers' live Razorpay key secrets, written by a "connect
your own gateway" flow that no checkout ever read. Deleting the endpoints
without dropping the table would leave payment credentials at rest that nothing
has a use for.
"""
import logging

import pytest

import db
from tests.conftest import TEST_PG_URL, raw_execute, raw_fetch_one


def redeploy(app_client):
    """Boot the app against the existing database, as a deploy does.

    Migrations run when the connection is opened, not on every init_db call, so
    the SQLite connection has to be dropped for this to be a real restart
    rather than a no-op.
    """
    if not TEST_PG_URL and db._sqlite_conn is not None:
        db._sqlite_conn.close()
        db._sqlite_conn = None
    app_client.portal.call(db.init_db)


def table_exists(name):
    try:
        raw_fetch_one(f"SELECT 1 FROM {name} LIMIT 1")
        return True
    except Exception:
        return False


def recreate_legacy_table():
    """Put the old table back, as an existing deployment still has it."""
    blob = "BYTEA" if TEST_PG_URL else "BLOB"
    raw_execute(f"""
        CREATE TABLE IF NOT EXISTS seller_gateways (
            seller_id TEXT PRIMARY KEY,
            key_id TEXT NOT NULL,
            key_secret_enc TEXT NOT NULL,
            webhook_secret_enc TEXT,
            enabled BOOLEAN,
            created_at TEXT NOT NULL
        )
    """)


def test_a_fresh_database_never_creates_it(app_client):
    assert not table_exists("seller_gateways")


def test_an_existing_deployment_has_it_dropped(app_client, caplog):
    recreate_legacy_table()
    raw_execute(
        "INSERT INTO seller_gateways (seller_id, key_id, key_secret_enc, created_at)"
        " VALUES ($1, $2, $3, $4)",
        "user_legacy", "rzp_live_abc123", "ciphertext", "2026-01-01T00:00:00+00:00")
    assert table_exists("seller_gateways")

    with caplog.at_level(logging.INFO, logger="stallwise.db"):
        redeploy(app_client)

    assert not table_exists("seller_gateways"), "the stored secrets are still there"
    # And it is on the record, so someone knows those keys need rotating.
    assert any("rotate" in r.message or "rotate" in str(r.args) for r in caplog.records), \
        [r.getMessage() for r in caplog.records]


def test_dropping_it_is_idempotent(app_client):
    redeploy(app_client)
    redeploy(app_client)
    assert not table_exists("seller_gateways")


def test_the_real_tables_survive_the_cleanup(app_client, seller_with_store):
    """A migration that drops things must not take anything else with it."""
    from tests.conftest import make_product

    product = make_product(seller_with_store, title="Survivor", price=250)
    redeploy(app_client)

    still_there = seller_with_store.get("/api/products").json()
    assert [p["title"] for p in still_there] == ["Survivor"]
    assert seller_with_store.get("/api/seller/route").json()["connected"] is True
