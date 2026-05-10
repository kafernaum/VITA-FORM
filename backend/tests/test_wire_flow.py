"""VITA-FORM iteration 7 — Wire transfer + bank accounts admin CRUD + revenue tests.

Covers:
- /api/admin/bank-accounts CRUD (create normalizes IBAN/currency, list, patch, delete)
- /api/bank-accounts (regular user, only active)
- /api/payments/wire/initiate (success + 404 inactive bank + 403 cross-user)
- /api/payments/wire/{txn_id}/confirm (success + double-confirm after paid)
- /api/admin/payments/pending listing of declared wires
- /api/admin/payments/{txn_id}/validate (idempotent: already_paid)
- /api/admin/payments/{txn_id}/reject
- /api/admin/revenue (by_currency / by_month / transactions_total)
- Regression: PayPal /api/payments/checkout still works
- 403 for non-admin on every /admin/* route
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get(
    "REACT_APP_BACKEND_URL") else "https://formation-finances.preview.emergentagent.com"
ADMIN_EMAIL = "admin@vita-form.com"
ADMIN_PASSWORD = "VitaForm2026!Admin"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "vitaform_db"


# ---- shared fixtures ----
@pytest.fixture(scope="session")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_auth(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    j = r.json()
    return j["access_token"], j["user"]["id"]


@pytest.fixture(scope="session")
def admin_headers(admin_auth):
    return {"Authorization": f"Bearer {admin_auth[0]}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def regular_user(session, db):
    """Create a non-VIP regular user TEST_user_<uuid>@vita-form.com."""
    suffix = uuid.uuid4().hex[:10]
    email = f"TEST_user_{suffix}@vita-form.com"
    pwd = "TestWire2026!"
    r = session.post(f"{BASE_URL}/api/auth/register",
                     json={"email": email, "password": pwd,
                           "full_name": "TEST Wire User"})
    assert r.status_code == 200, r.text
    j = r.json()
    token = j["access_token"]
    user_id = j["user"]["id"]
    yield {"email": email, "password": pwd, "token": token, "id": user_id,
           "headers": {"Authorization": f"Bearer {token}",
                       "Content-Type": "application/json"}}
    # teardown
    db.users.delete_one({"id": user_id})
    db.generations.delete_many({"user_id": user_id})
    db.payment_transactions.delete_many({"user_id": user_id})


@pytest.fixture(scope="session")
def regular_user_2(session, db):
    """A second regular user for cross-user 403 test."""
    suffix = uuid.uuid4().hex[:10]
    email = f"TEST_user2_{suffix}@vita-form.com"
    pwd = "TestWire2026!"
    r = session.post(f"{BASE_URL}/api/auth/register",
                     json={"email": email, "password": pwd,
                           "full_name": "TEST Wire User 2"})
    assert r.status_code == 200, r.text
    j = r.json()
    user_id = j["user"]["id"]
    yield {"email": email, "token": j["access_token"], "id": user_id,
           "headers": {"Authorization": f"Bearer {j['access_token']}",
                       "Content-Type": "application/json"}}
    db.users.delete_one({"id": user_id})


@pytest.fixture(scope="session")
def fake_generation(db, regular_user):
    """Insert a generation owned by the regular user."""
    gen_id = f"TEST_GEN_{uuid.uuid4()}"
    db.generations.insert_one({
        "id": gen_id,
        "user_id": regular_user["id"],
        "topic": "TEST wire flow generation",
        "institution_name": "TEST",
        "country": "France",
        "cycle": "Master",
        "duration": "1 jour",
        "year": 2026,
        "language": "fr",
        "content": "TEST content for wire paywall",
        "kind": "course",
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    yield gen_id
    db.generations.delete_one({"id": gen_id})
    db.payment_transactions.delete_many({"generation_id": gen_id})


@pytest.fixture(scope="session")
def created_bank_active(session, admin_headers, db):
    """Seed an ACTIVE bank account; cleanup at session end."""
    payload = {
        "holder_name": "TEST VITA-FORM SARL",
        "bank_name": "TEST Banque Postale",
        "iban": "FR76 3000 1007 9412 3456 7890 185",
        "bic": "BDFEFRPPXXX",
        "currency": "eur",
        "country": "France",
        "instructions": "TEST account - wire flow",
        "is_active": True,
    }
    r = session.post(f"{BASE_URL}/api/admin/bank-accounts",
                     headers=admin_headers, json=payload)
    assert r.status_code == 200, r.text
    acct = r.json()
    yield acct
    db.bank_accounts.delete_one({"id": acct["id"]})


@pytest.fixture(scope="session")
def created_bank_inactive(session, admin_headers, db):
    payload = {
        "holder_name": "TEST INACTIVE",
        "bank_name": "TEST Inactive Bank",
        "iban": "DE89370400440532013000",
        "bic": "COBADEFFXXX",
        "currency": "EUR",
        "country": "Germany",
        "is_active": False,
    }
    r = session.post(f"{BASE_URL}/api/admin/bank-accounts",
                     headers=admin_headers, json=payload)
    assert r.status_code == 200, r.text
    acct = r.json()
    yield acct
    db.bank_accounts.delete_one({"id": acct["id"]})


# ---- BANK ACCOUNTS CRUD ----
def test_admin_create_bank_normalizes(created_bank_active):
    a = created_bank_active
    assert a["id"]
    # IBAN spaces removed and uppercased
    assert a["iban"] == "FR7630001007941234567890185"
    # Currency uppercased
    assert a["currency"] == "EUR"
    assert a["holder_name"] == "TEST VITA-FORM SARL"
    assert a["is_active"] is True
    assert "_id" not in a


def test_admin_list_bank_accounts(session, admin_headers,
                                   created_bank_active, created_bank_inactive):
    r = session.get(f"{BASE_URL}/api/admin/bank-accounts",
                    headers=admin_headers)
    assert r.status_code == 200
    items = r.json()
    ids = {b["id"] for b in items}
    assert created_bank_active["id"] in ids
    assert created_bank_inactive["id"] in ids
    assert all("_id" not in b for b in items)


def test_user_list_bank_accounts_only_active(session, regular_user,
                                              created_bank_active,
                                              created_bank_inactive):
    r = session.get(f"{BASE_URL}/api/bank-accounts",
                    headers=regular_user["headers"])
    assert r.status_code == 200
    items = r.json()
    ids = {b["id"] for b in items}
    assert created_bank_active["id"] in ids
    assert created_bank_inactive["id"] not in ids


def test_admin_patch_bank_account(session, admin_headers, created_bank_active):
    aid = created_bank_active["id"]
    update = {**created_bank_active,
              "holder_name": "TEST VITA-FORM UPDATED",
              "is_active": True}
    # Pydantic input model expects only its declared fields; remove extras
    update = {k: v for k, v in update.items() if k in {
        "holder_name", "bank_name", "iban", "bic", "currency",
        "country", "instructions", "is_active"}}
    r = session.patch(f"{BASE_URL}/api/admin/bank-accounts/{aid}",
                      headers=admin_headers, json=update)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["holder_name"] == "TEST VITA-FORM UPDATED"
    assert "_id" not in j


def test_admin_patch_bank_account_404(session, admin_headers):
    payload = {"holder_name": "TEST X", "bank_name": "TEST Bank",
               "iban": "FR1420041010050500013M02606", "currency": "EUR"}
    r = session.patch(f"{BASE_URL}/api/admin/bank-accounts/non-existent-xyz",
                      headers=admin_headers, json=payload)
    assert r.status_code == 404


def test_admin_delete_bank_account(session, admin_headers, db):
    # create-then-delete (own lifecycle so we don't break other tests)
    payload = {"holder_name": "TEST DEL", "bank_name": "TEST Del Bank",
               "iban": "GB29NWBK60161331926819", "bic": "NWBKGB2L",
               "currency": "GBP", "is_active": True}
    r = session.post(f"{BASE_URL}/api/admin/bank-accounts",
                     headers=admin_headers, json=payload)
    assert r.status_code == 200
    aid = r.json()["id"]

    d = session.delete(f"{BASE_URL}/api/admin/bank-accounts/{aid}",
                       headers=admin_headers)
    assert d.status_code == 200
    assert d.json() == {"status": "ok"}

    # second delete returns 404
    d2 = session.delete(f"{BASE_URL}/api/admin/bank-accounts/{aid}",
                        headers=admin_headers)
    assert d2.status_code == 404


# ---- WIRE INITIATE ----
def test_wire_initiate_success(session, regular_user, fake_generation,
                                 created_bank_active, db):
    r = session.post(f"{BASE_URL}/api/payments/wire/initiate",
                     headers=regular_user["headers"],
                     json={"generation_id": fake_generation,
                           "bank_account_id": created_bank_active["id"],
                           "currency": "EUR"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert "txn_id" in j and j["txn_id"]
    assert j["wire_reference"].startswith("VF-")
    assert len(j["wire_reference"]) == 11  # VF-XXXXXXXX (3 + 8)
    assert j["amount"] == 14.90
    assert j["currency"] == "EUR"
    assert isinstance(j["bank_account"], dict)
    assert j["bank_account"]["id"] == created_bank_active["id"]
    assert isinstance(j["instructions"], str) and j["instructions"]

    # verify mongo row
    txn = db.payment_transactions.find_one({"id": j["txn_id"]}, {"_id": 0})
    assert txn is not None
    assert txn["provider"] == "wire"
    assert txn["status"] == "awaiting_wire"
    assert txn["payment_status"] == "pending"
    assert txn["wire_reference"] == j["wire_reference"]
    assert txn["currency"] == "EUR"
    assert txn["amount"] == 14.90


def test_wire_initiate_inactive_bank_404(session, regular_user, fake_generation,
                                           created_bank_inactive):
    r = session.post(f"{BASE_URL}/api/payments/wire/initiate",
                     headers=regular_user["headers"],
                     json={"generation_id": fake_generation,
                           "bank_account_id": created_bank_inactive["id"],
                           "currency": "EUR"})
    assert r.status_code == 404, r.text


def test_wire_initiate_someone_elses_generation_403(session, regular_user_2,
                                                      fake_generation,
                                                      created_bank_active):
    # regular_user_2 tries to pay for regular_user's generation
    r = session.post(f"{BASE_URL}/api/payments/wire/initiate",
                     headers=regular_user_2["headers"],
                     json={"generation_id": fake_generation,
                           "bank_account_id": created_bank_active["id"],
                           "currency": "EUR"})
    assert r.status_code == 403, r.text


# ---- WIRE CONFIRM + ADMIN VALIDATE / REJECT / PENDING / REVENUE ----
@pytest.fixture
def initiated_wire(session, regular_user, fake_generation, created_bank_active):
    r = session.post(f"{BASE_URL}/api/payments/wire/initiate",
                     headers=regular_user["headers"],
                     json={"generation_id": fake_generation,
                           "bank_account_id": created_bank_active["id"],
                           "currency": "EUR"})
    assert r.status_code == 200
    return r.json()


def test_wire_confirm_and_admin_pending(session, admin_headers, regular_user,
                                          initiated_wire):
    txn_id = initiated_wire["txn_id"]
    r = session.post(f"{BASE_URL}/api/payments/wire/{txn_id}/confirm",
                     headers=regular_user["headers"],
                     json={"reference": "BNK-REF-12345",
                           "sender_name": "TEST Sender Lastname",
                           "sender_note": "Paiement formation"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "declared"
    assert j["txn_id"] == txn_id

    p = session.get(f"{BASE_URL}/api/admin/payments/pending",
                    headers=admin_headers)
    assert p.status_code == 200
    rows = p.json()
    found = next((x for x in rows if x["id"] == txn_id), None)
    assert found is not None, "declared wire missing from pending list"
    assert found["status"] == "wire_declared"
    assert found["wire_sender_name"] == "TEST Sender Lastname"
    assert found["wire_user_reference"] == "BNK-REF-12345"
    assert "generation_topic" in found


def test_wire_admin_validate_then_already_paid(session, admin_headers,
                                                  regular_user, initiated_wire,
                                                  fake_generation, db):
    txn_id = initiated_wire["txn_id"]
    # confirm first
    c = session.post(f"{BASE_URL}/api/payments/wire/{txn_id}/confirm",
                     headers=regular_user["headers"],
                     json={"reference": "REF-X", "sender_name": "TEST Sender"})
    assert c.status_code == 200

    # validate
    v = session.post(f"{BASE_URL}/api/admin/payments/{txn_id}/validate",
                    headers=admin_headers)
    assert v.status_code == 200, v.text
    assert v.json()["status"] == "validated"

    # generation is now paid=true
    gen = db.generations.find_one({"id": fake_generation}, {"_id": 0})
    assert gen["paid"] is True
    assert gen.get("payment_txn_id") == txn_id

    # txn payment_status = paid
    txn = db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    assert txn["payment_status"] == "paid"

    # re-validate -> already_paid
    v2 = session.post(f"{BASE_URL}/api/admin/payments/{txn_id}/validate",
                     headers=admin_headers)
    assert v2.status_code == 200
    assert v2.json()["status"] == "already_paid"

    # confirm AFTER paid -> 400 'Déjà validé'
    c2 = session.post(f"{BASE_URL}/api/payments/wire/{txn_id}/confirm",
                      headers=regular_user["headers"],
                      json={"reference": "REF-Y", "sender_name": "TEST 2"})
    assert c2.status_code == 400
    detail = c2.json().get("detail", "")
    assert "Déjà" in detail or "Deja" in detail or "validé" in detail.lower()


def test_wire_admin_reject(session, admin_headers, initiated_wire, db):
    txn_id = initiated_wire["txn_id"]
    r = session.post(
        f"{BASE_URL}/api/admin/payments/{txn_id}/reject?reason=insufficient",
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"
    txn = db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    assert txn["status"] == "rejected"
    assert txn.get("rejection_reason") == "insufficient"


def test_admin_reject_404(session, admin_headers):
    r = session.post(
        f"{BASE_URL}/api/admin/payments/non-existent/reject?reason=x",
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_admin_revenue(session, admin_headers):
    """Run AFTER at least one validated wire (test_wire_admin_validate ran)."""
    r = session.get(f"{BASE_URL}/api/admin/revenue", headers=admin_headers)
    assert r.status_code == 200
    j = r.json()
    assert "by_currency" in j and "by_month" in j and "transactions_total" in j
    assert isinstance(j["by_currency"], dict)
    assert isinstance(j["by_month"], list)
    assert j["transactions_total"] >= 1
    # We just paid 14.90 EUR via wire -> EUR row exists
    assert "EUR" in j["by_currency"]
    eur = j["by_currency"]["EUR"]
    assert eur["count"] >= 1
    assert eur["total"] >= 14.90 - 0.001


# ---- ADMIN AUTHORIZATION ----
def test_admin_endpoints_forbid_regular_user(session, regular_user,
                                                created_bank_active):
    h = regular_user["headers"]
    paths = [
        ("get", "/api/admin/bank-accounts"),
        ("post", "/api/admin/bank-accounts"),
        ("get", "/api/admin/payments/pending"),
        ("get", "/api/admin/revenue"),
        ("post", f"/api/admin/payments/abc/validate"),
        ("post", f"/api/admin/payments/abc/reject"),
        ("patch", f"/api/admin/bank-accounts/{created_bank_active['id']}"),
        ("delete", f"/api/admin/bank-accounts/{created_bank_active['id']}"),
    ]
    for method, p in paths:
        url = BASE_URL + p
        r = session.request(method, url, headers=h, json={})
        assert r.status_code == 403, f"{method} {p} -> {r.status_code}, expected 403"


# ---- PAYPAL REGRESSION ----
def test_paypal_checkout_regression(session, regular_user, fake_generation):
    r = session.post(f"{BASE_URL}/api/payments/checkout",
                     headers=regular_user["headers"],
                     json={"generation_id": fake_generation,
                           "origin_url": BASE_URL,
                           "currency": "EUR"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["url"].startswith("https://www.paypal.com/cgi-bin/webscr?cmd=_xclick")
    assert j["currency"] == "EUR"
    assert j["amount"] == 14.90
    assert j["txn_id"]
