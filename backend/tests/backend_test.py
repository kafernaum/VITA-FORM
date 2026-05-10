"""VITA-FORM backend integration tests (pytest)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://formation-finances.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@vita-form.com"
ADMIN_PASSWORD = "VitaForm2026!Admin"

# Long timeout for LLM calls (30-90s expected)
LLM_TIMEOUT = 240


# --- Fixtures -----------------------------------------------------------------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                     timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "admin"
    assert data["user"]["vip"] is True
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def user_creds():
    ts = int(time.time())
    return {
        "email": f"apprenant.test+{ts}@vita-form.com",
        "password": "Apprenant2026!",
        "full_name": "Apprenant Test",
    }


@pytest.fixture(scope="session")
def user_token(session, user_creds):
    r = session.post(f"{BASE_URL}/api/auth/register", json=user_creds, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def user_headers(user_token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"}


@pytest.fixture(scope="session")
def french_institution_id(session):
    r = session.get(f"{BASE_URL}/api/institutions", params={"country_code": "FR"}, timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0, "No French institutions found"
    return items[0]["id"]


# Shared state across course-generation flow
state = {}


# --- Health -------------------------------------------------------------------
def test_root(session):
    r = session.get(f"{BASE_URL}/api/", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert data.get("app") == "VITA-FORM"
    assert data.get("status") == "ok"


# --- Auth ---------------------------------------------------------------------
def test_login_admin(admin_token):
    assert isinstance(admin_token, str) and len(admin_token) > 20


def test_register_user(user_token):
    assert isinstance(user_token, str) and len(user_token) > 20


def test_register_duplicate_email(session, user_creds):
    r = session.post(f"{BASE_URL}/api/auth/register", json=user_creds, timeout=30)
    assert r.status_code == 400


def test_auth_me_admin(session, admin_headers):
    r = session.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    u = r.json()
    assert u["email"] == ADMIN_EMAIL
    assert u["role"] == "admin"
    assert u.get("vip") is True


def test_auth_me_no_token(session):
    r = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert r.status_code == 401


# --- Meta / Institutions ------------------------------------------------------
def test_meta_options(session):
    r = session.get(f"{BASE_URL}/api/meta/options", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "cycles" in d and isinstance(d["cycles"], list) and len(d["cycles"]) > 0
    assert "durations" in d and isinstance(d["durations"], list) and len(d["durations"]) > 0
    assert "daily_salaries" in d and isinstance(d["daily_salaries"], dict)
    assert "FR" in d["daily_salaries"]


def test_institutions_count(session):
    r = session.get(f"{BASE_URL}/api/institutions", timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 22, f"Expected ≥22 institutions, got {len(items)}"


def test_institutions_filter_fr(session):
    r = session.get(f"{BASE_URL}/api/institutions", params={"country_code": "FR"}, timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 5
    for it in items:
        assert it["country_code"] == "FR"


# --- Course generation (LLM, slow) -------------------------------------------
def test_create_generation_admin(session, admin_headers, french_institution_id):
    payload = {
        "topic": "La dette publique sous l'angle vitaliste",
        "institution_id": french_institution_id,
        "cycle": "Master 2",
        "duration": "3 mois",
    }
    r = session.post(f"{BASE_URL}/api/generations", headers=admin_headers,
                     json=payload, timeout=LLM_TIMEOUT)
    assert r.status_code == 200, f"Generation failed: {r.status_code} {r.text[:500]}"
    d = r.json()
    assert "id" in d
    assert d.get("unlocked") is True, "Admin must see unlocked=True"
    assert d.get("institution_name")
    content = d.get("content", "")
    assert isinstance(content, str) and len(content) > 200, "Content too short"
    state["gen_id"] = d["id"]


def test_get_my_generations_admin(session, admin_headers):
    r = session.get(f"{BASE_URL}/api/generations", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any(it["id"] == state.get("gen_id") for it in items)


def test_get_generation_admin_full(session, admin_headers):
    gen_id = state.get("gen_id")
    assert gen_id, "Need previous generation"
    r = session.get(f"{BASE_URL}/api/generations/{gen_id}", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["unlocked"] is True
    # Admin sees full content (no truncation marker)
    assert "aperçu tronqué" not in d.get("content", "")


def test_download_pdf_admin(session, admin_headers):
    gen_id = state.get("gen_id")
    r = session.get(f"{BASE_URL}/api/generations/{gen_id}/download/pdf",
                    headers=admin_headers, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF", "PDF magic header missing"


def test_download_docx_admin(session, admin_headers):
    gen_id = state.get("gen_id")
    r = session.get(f"{BASE_URL}/api/generations/{gen_id}/download/docx",
                    headers=admin_headers, timeout=60)
    assert r.status_code == 200
    # DOCX is a zip file (magic PK)
    assert r.content[:2] == b"PK"


def test_download_slides_admin(session, admin_headers):
    gen_id = state.get("gen_id")
    r = session.get(f"{BASE_URL}/api/generations/{gen_id}/download/slides",
                    headers=admin_headers, timeout=60)
    assert r.status_code == 200
    assert "html" in r.headers.get("content-type", "").lower()


# --- Paywall: non-VIP user flow ----------------------------------------------
def test_user_create_generation_and_paywall(session, user_headers, french_institution_id):
    payload = {
        "topic": "Budget participatif et logique vitaliste",
        "institution_id": french_institution_id,
        "cycle": "Licence 3",
        "duration": "2 mois",
    }
    r = session.post(f"{BASE_URL}/api/generations", headers=user_headers,
                     json=payload, timeout=LLM_TIMEOUT)
    assert r.status_code == 200, f"User generation failed: {r.status_code} {r.text[:300]}"
    d = r.json()
    assert d.get("unlocked") is False, "Non-VIP user must see unlocked=False"
    state["user_gen_id"] = d["id"]
    # Content should be truncated
    content = d.get("content", "")
    assert len(content) <= 1500


def test_user_download_blocked_402(session, user_headers):
    gen_id = state.get("user_gen_id")
    assert gen_id
    r = session.get(f"{BASE_URL}/api/generations/{gen_id}/download/pdf",
                    headers=user_headers, timeout=60)
    assert r.status_code == 402, f"Expected 402 for paywall, got {r.status_code}"


def test_mock_checkout_unlocks(session, user_headers):
    gen_id = state.get("user_gen_id")
    r = session.post(f"{BASE_URL}/api/payments/mock-checkout",
                     headers=user_headers,
                     json={"generation_id": gen_id, "method": "card"},
                     timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "succeeded"
    assert "payment_id" in d

    # Subsequent GET shows unlocked=True
    r2 = session.get(f"{BASE_URL}/api/generations/{gen_id}", headers=user_headers, timeout=30)
    assert r2.status_code == 200
    assert r2.json().get("unlocked") is True

    # Now download must work
    r3 = session.get(f"{BASE_URL}/api/generations/{gen_id}/download/pdf",
                     headers=user_headers, timeout=60)
    assert r3.status_code == 200
    assert r3.content[:4] == b"%PDF"


# --- Vitalist analyze ---------------------------------------------------------
def test_vitalist_analyze(session, admin_headers):
    payload = {
        "document_type": "Budget",
        "monetary_amount": 1_000_000,
        "country_code": "FR",
        "document_text": ("Le budget proposé par la commune comporte une enveloppe "
                          "destinée à la rénovation urbaine, et soulève des questions "
                          "vitalistes essentielles sur l'allocation de ressources."),
        "title": "Test analyse vitaliste",
    }
    r = session.post(f"{BASE_URL}/api/vitalist/analyze", headers=admin_headers,
                     json=payload, timeout=LLM_TIMEOUT)
    assert r.status_code == 200, f"Vitalist analyze failed: {r.status_code} {r.text[:300]}"
    d = r.json()
    assert "id" in d
    assert "content" in d and len(d["content"]) > 100
    metrics = d.get("metrics", {})
    assert metrics, "metrics missing"
    # 1_000_000 / 130 ≈ 7692
    assert 7000 <= metrics["life_days"] <= 8500, f"life_days={metrics['life_days']}"
    assert metrics["life_months"] > 0
    assert metrics["life_years"] > 0


# --- Admin endpoints ----------------------------------------------------------
def test_admin_users_list(session, admin_headers):
    r = session.get(f"{BASE_URL}/api/admin/users", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) >= 1
    sample = items[0]
    assert "generations_count" in sample
    assert "payments_count" in sample
    assert "password_hash" not in sample


def test_admin_users_forbidden_for_user(session, user_headers):
    r = session.get(f"{BASE_URL}/api/admin/users", headers=user_headers, timeout=30)
    assert r.status_code == 403


def test_admin_grant_vip(session, admin_headers, user_token):
    # Get user id from /auth/me with user token
    me = requests.get(f"{BASE_URL}/api/auth/me",
                      headers={"Authorization": f"Bearer {user_token}"}, timeout=30).json()
    user_id = me["id"]
    r = session.post(f"{BASE_URL}/api/admin/users/{user_id}/vip",
                     headers=admin_headers, params={"vip": "true", "days": 30}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("vip") is True
    assert d.get("until")


def test_admin_stats(session, admin_headers):
    r = session.get(f"{BASE_URL}/api/admin/stats", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("users", "generations", "payments", "institutions"):
        assert k in d
        assert isinstance(d[k], int)


def test_admin_institution_create_delete(session, admin_headers):
    payload = {
        "name": "TEST_Institut Vitaliste Pytest",
        "country": "France",
        "country_code": "FR",
        "city": "Paris",
        "type": "Test",
    }
    r = session.post(f"{BASE_URL}/api/admin/institutions",
                     headers=admin_headers, json=payload, timeout=30)
    assert r.status_code == 200
    inst = r.json()
    assert inst["id"]
    assert inst["name"] == payload["name"]

    rd = session.delete(f"{BASE_URL}/api/admin/institutions/{inst['id']}",
                        headers=admin_headers, timeout=30)
    assert rd.status_code == 200
    assert rd.json().get("status") == "ok"

    # 404 on second delete
    rd2 = session.delete(f"{BASE_URL}/api/admin/institutions/{inst['id']}",
                         headers=admin_headers, timeout=30)
    assert rd2.status_code == 404
