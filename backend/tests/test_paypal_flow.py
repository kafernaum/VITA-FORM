"""VITA-FORM iteration 6 — PayPal _xclick flow tests.

Covers:
- Health, login, payment options
- Checkout URL build (EUR + USD pricing, invalid currency, unknown gen_id)
- Status polling (valid + 404)
- IPN webhook (empty / no custom / unknown txn → fake payload should fail verify)
- Removed Stripe webhook returns 404
- Smoke: institutions, jurisprudences counts
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://formation-finances.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@vita-form.com"
ADMIN_PASSWORD = "VitaForm2026!Admin"

# Direct mongo client to insert a fake generation (LLM may be 402)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "vitaform_db"


@pytest.fixture(scope="session")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
    return data["access_token"], data["user"]["id"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    token, _ = admin_token
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def fake_generation(db, admin_token):
    """Insert a generation owned by the admin so checkout passes ownership check."""
    _, user_id = admin_token
    gen_id = f"TEST_GEN_{uuid.uuid4()}"
    doc = {
        "id": gen_id,
        "user_id": user_id,
        "topic": "TEST PayPal flow generation",
        "institution_id": None,
        "institution_name": "TEST",
        "country": "France",
        "cycle": "Master",
        "duration": "Test",
        "year": 2026,
        "language": "fr",
        "content": "TEST content for paywall",
        "kind": "course",
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.generations.insert_one(doc)
    yield gen_id
    db.generations.delete_one({"id": gen_id})
    db.payment_transactions.delete_many({"generation_id": gen_id})


# --- Smoke ---
def test_healthcheck(session):
    r = session.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
    assert j.get("app") == "VITA-FORM"


def test_admin_login(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"


def test_institutions_count(session):
    r = session.get(f"{BASE_URL}/api/institutions")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 22, f"expected ≥22 institutions, got {len(items)}"


def test_jurisprudences_count(session, admin_headers):
    r = session.get(f"{BASE_URL}/api/jurisprudences?limit=100", headers=admin_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 22, f"expected ≥22 jurisprudences, got {len(items)}"


# --- Payment options ---
def test_payment_options(session):
    r = session.get(f"{BASE_URL}/api/payments/options")
    assert r.status_code == 200
    j = r.json()
    assert j["currencies"] == ["EUR", "USD", "GBP", "CAD", "CHF", "AUD", "JPY"]
    assert j["default_currency"] == "EUR"
    assert j["merchant_email"] == "ely.mustapha@yahoo.ca"
    prices = j["prices"]
    for c in ["EUR", "USD", "GBP", "CAD", "CHF", "AUD", "JPY"]:
        assert c in prices, f"price missing for {c}"
    assert prices["EUR"] == 14.90
    assert prices["USD"] == 16.00


# --- Checkout build ---
def _checkout(session, headers, gen_id, currency="EUR"):
    return session.post(
        f"{BASE_URL}/api/payments/checkout",
        headers=headers,
        json={
            "generation_id": gen_id,
            "origin_url": "https://formation-finances.preview.emergentagent.com",
            "currency": currency,
        },
    )


def test_checkout_eur(session, admin_headers, fake_generation):
    r = _checkout(session, admin_headers, fake_generation, "EUR")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["currency"] == "EUR"
    assert j["amount"] == 14.90
    assert "txn_id" in j and j["txn_id"]
    url = j["url"]
    assert url.startswith("https://www.paypal.com/cgi-bin/webscr?cmd=_xclick"), url
    qs = parse_qs(urlparse(url).query)
    assert qs["business"][0] == "ely.mustapha@yahoo.ca"
    assert qs["merchant_id"][0] == "XGYL8NPMKHDUY"
    assert qs["currency_code"][0] == "EUR"
    assert qs["amount"][0] == "14.90"
    assert qs["custom"][0] == j["txn_id"]
    assert "/api/webhook/paypal" in qs["notify_url"][0]


def test_checkout_usd_pricing(session, admin_headers, fake_generation):
    r = _checkout(session, admin_headers, fake_generation, "USD")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["currency"] == "USD"
    assert j["amount"] == 16.00
    qs = parse_qs(urlparse(j["url"]).query)
    assert qs["amount"][0] == "16.00"
    assert qs["currency_code"][0] == "USD"


def test_checkout_invalid_currency(session, admin_headers, fake_generation):
    r = _checkout(session, admin_headers, fake_generation, "XAF")
    assert r.status_code == 400


def test_checkout_unknown_generation(session, admin_headers):
    r = _checkout(session, admin_headers, "non-existent-id-xxx", "EUR")
    assert r.status_code == 404


# --- Status ---
def test_checkout_status_valid(session, admin_headers, fake_generation):
    r = _checkout(session, admin_headers, fake_generation, "EUR")
    assert r.status_code == 200
    txn_id = r.json()["txn_id"]

    s = session.get(f"{BASE_URL}/api/payments/checkout/status/{txn_id}",
                    headers=admin_headers)
    assert s.status_code == 200
    j = s.json()
    assert j["txn_id"] == txn_id
    assert j["status"] == "initiated"
    assert j["payment_status"] == "pending"
    assert j["currency"] == "EUR"
    assert j["amount"] == 14.90
    assert j["generation_id"] == fake_generation


def test_checkout_status_unknown(session, admin_headers):
    r = session.get(f"{BASE_URL}/api/payments/checkout/status/unknown-txn-xyz",
                    headers=admin_headers)
    assert r.status_code == 404


# --- Webhook ---
def test_webhook_empty():
    r = requests.post(f"{BASE_URL}/api/webhook/paypal", data="")
    assert r.status_code == 200
    assert r.json() == {"status": "empty"}


def test_webhook_no_custom():
    r = requests.post(
        f"{BASE_URL}/api/webhook/paypal",
        data="payment_status=Completed&mc_gross=14.90",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ignored"}


def test_webhook_unknown_txn_or_invalid():
    """Fake IPN with custom=unknown — PayPal verify will return INVALID,
    so we accept either 'invalid' (verify failed) or 'unknown_txn'."""
    body = (
        "custom=does-not-exist-xyz&payment_status=Completed&mc_gross=14.90"
        "&mc_currency=EUR&receiver_email=ely.mustapha%40yahoo.ca"
    )
    r = requests.post(
        f"{BASE_URL}/api/webhook/paypal",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    assert r.status_code == 200
    assert r.json().get("status") in ("invalid", "unknown_txn")


# --- Removed Stripe endpoints ---
def test_stripe_webhook_removed():
    r = requests.post(f"{BASE_URL}/api/webhook/stripe", data="{}",
                      headers={"Content-Type": "application/json"})
    assert r.status_code == 404, f"stripe webhook should be removed, got {r.status_code}"


def test_mock_checkout_removed(session, admin_headers, fake_generation):
    r = session.post(
        f"{BASE_URL}/api/payments/mock-checkout",
        headers=admin_headers,
        json={"generation_id": fake_generation},
    )
    assert r.status_code in (404, 405)
