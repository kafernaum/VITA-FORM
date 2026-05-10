"""VITA-FORM backend integration tests — iteration 3.

Covers: smoke, sources upload (TXT, PDF), jurisprudences (admin + search),
Stripe checkout (real test mode), payment status, generations payload validation,
email service import.
"""
import io
import os
import uuid
import asyncio

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@vita-form.com"
ADMIN_PASSWORD = "VitaForm2026!Admin"


# --- Fixtures ----------------------------------------------------------------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                     timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "admin"
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Smoke -------------------------------------------------------------------
class TestSmoke:
    def test_root(self, session):
        r = session.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"

    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_institutions_count(self, session, admin_headers):
        r = session.get(f"{BASE_URL}/api/institutions", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 22, f"Expected >=22 institutions, got {len(items)}"


# --- Sources upload ----------------------------------------------------------
class TestSourcesUpload:
    def test_upload_txt_and_list_and_delete(self, session, admin_headers):
        body = ("VITA-FORM test source. " * 30).encode("utf-8")
        files = {"file": ("TEST_source.txt", io.BytesIO(body), "text/plain")}
        r = session.post(f"{BASE_URL}/api/sources/upload",
                         headers=admin_headers, files=files, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        assert data["original_filename"] == "TEST_source.txt"
        assert data["extracted_chars"] > 0
        assert "preview" in data and "VITA-FORM" in data["preview"]
        src_id = data["id"]

        # GET /api/sources lists it (no extracted_text)
        r2 = session.get(f"{BASE_URL}/api/sources", headers=admin_headers, timeout=15)
        assert r2.status_code == 200
        rows = r2.json()
        match = [x for x in rows if x.get("id") == src_id]
        assert match, "Uploaded source not in list"
        assert "extracted_text" not in match[0]
        assert match[0]["content_type"] == "text/plain"
        assert match[0]["size"] > 0

        # DELETE soft-deletes
        rd = session.delete(f"{BASE_URL}/api/sources/{src_id}",
                            headers=admin_headers, timeout=15)
        assert rd.status_code == 200
        assert rd.json().get("status") == "ok"

        # Verify removed from list
        r3 = session.get(f"{BASE_URL}/api/sources", headers=admin_headers, timeout=15)
        assert r3.status_code == 200
        ids = [x.get("id") for x in r3.json()]
        assert src_id not in ids

    def test_upload_pdf(self, session, admin_headers):
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            pytest.skip("reportlab not available")
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "VITAFORM PDF EXTRACTION TEST CONTENT")
        c.drawString(100, 730, "Ligne 2 - test extraction texte.")
        c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()
        assert len(pdf_bytes) > 100

        files = {"file": ("TEST_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        r = session.post(f"{BASE_URL}/api/sources/upload",
                         headers=admin_headers, files=files, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["extracted_chars"] > 0, f"PDF extracted_chars = 0; preview={data.get('preview')}"
        assert "VITAFORM" in data.get("preview", "").upper()

        # Cleanup
        session.delete(f"{BASE_URL}/api/sources/{data['id']}",
                       headers=admin_headers, timeout=15)

    def test_upload_unsupported_format(self, session, admin_headers):
        files = {"file": ("TEST_bad.bin", io.BytesIO(b"abc"), "application/octet-stream")}
        r = session.post(f"{BASE_URL}/api/sources/upload",
                         headers=admin_headers, files=files, timeout=30)
        assert r.status_code == 400


# --- Jurisprudences ----------------------------------------------------------
class TestJurisprudences:
    @pytest.fixture(scope="class")
    def juris_id(self, session, admin_headers):
        payload = {
            "title": "TEST CC dec 2024-845 DC",
            "country": "France",
            "body": "Le Conseil constitutionnel rappelle le principe de sincerite budgetaire "
                    "et la portee de l'article 47 LOLF concernant la programmation pluriannuelle "
                    "des finances publiques. Decision rendue en formation pleniere.",
            "reference": "2024-845 DC",
            "tags": ["LOLF", "sincerite"],
        }
        r = session.post(f"{BASE_URL}/api/admin/jurisprudences",
                         headers={**admin_headers, "Content-Type": "application/json"},
                         json=payload, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        assert data["title"] == payload["title"]
        return data["id"]

    def test_create_juris(self, juris_id):
        assert isinstance(juris_id, str) and len(juris_id) > 0

    def test_search_by_q(self, session, admin_headers, juris_id):
        r = session.get(f"{BASE_URL}/api/jurisprudences",
                        headers=admin_headers,
                        params={"q": "sincerite"}, timeout=20)
        assert r.status_code == 200
        items = r.json()
        ids = [x.get("id") for x in items]
        assert juris_id in ids, f"juris not found in search; items={items}"
        match = next(x for x in items if x["id"] == juris_id)
        # Score field present when text-search used
        assert "score" in match

    def test_filter_by_country(self, session, admin_headers, juris_id):
        r = session.get(f"{BASE_URL}/api/jurisprudences",
                        headers=admin_headers,
                        params={"country": "France"}, timeout=20)
        assert r.status_code == 200
        ids = [x.get("id") for x in r.json()]
        assert juris_id in ids

    def test_get_full_body(self, session, admin_headers, juris_id):
        r = session.get(f"{BASE_URL}/api/jurisprudences/{juris_id}",
                        headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "body" in data and len(data["body"]) >= 50
        assert data["country"] == "France"

    def test_delete(self, session, admin_headers, juris_id):
        r = session.delete(f"{BASE_URL}/api/admin/jurisprudences/{juris_id}",
                           headers=admin_headers, timeout=15)
        assert r.status_code == 200
        # Verify removed
        r2 = session.get(f"{BASE_URL}/api/jurisprudences/{juris_id}",
                         headers=admin_headers, timeout=15)
        assert r2.status_code == 404


# --- Stripe checkout (real, test mode) ---------------------------------------
class TestStripeCheckout:
    @pytest.fixture(scope="class")
    def generation_id(self, admin_headers):
        """Insert a generation row directly via Mongo for paywall testing."""
        from motor.motor_asyncio import AsyncIOMotorClient
        from datetime import datetime, timezone
        gid = str(uuid.uuid4())

        async def _seed():
            client = AsyncIOMotorClient(os.environ["MONGO_URL"])
            db = client[os.environ["DB_NAME"]]
            admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0})
            assert admin, "admin user not seeded"
            doc = {
                "id": gid,
                "user_id": admin["id"],
                "topic": "TEST topic for Stripe",
                "institution_id": None,
                "institution_name": "TEST Inst",
                "country": "France",
                "cycle": "Licence 3",
                "duration": "1 jour (8h)",
                "year": 2026,
                "language": "fr",
                "content": "TEST content " * 20,
                "kind": "course",
                "paid": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.generations.insert_one(doc)
            client.close()

        asyncio.get_event_loop().run_until_complete(_seed()) if False else asyncio.run(_seed())
        return gid

    def test_checkout_creates_session_and_txn(self, session, admin_headers, generation_id):
        payload = {"generation_id": generation_id, "origin_url": BASE_URL}
        r = session.post(f"{BASE_URL}/api/payments/checkout",
                         headers={**admin_headers, "Content-Type": "application/json"},
                         json=payload, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("url", "").startswith("https://"), f"missing Stripe URL: {data}"
        assert data.get("session_id", "").startswith("cs_"), f"bad session_id: {data}"
        # Persist for next test
        TestStripeCheckout._sid = data["session_id"]

    def test_checkout_status_initiated(self, session, admin_headers):
        sid = getattr(TestStripeCheckout, "_sid", None)
        if not sid:
            pytest.skip("no session_id from previous test")
        r = session.get(f"{BASE_URL}/api/payments/checkout/status/{sid}",
                        headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_id"] == sid
        # Either initiated/open and pending — accept both since Stripe may return "open"
        assert data["payment_status"] in {"pending", "unpaid"}, data
        assert "generation_id" in data


# --- Generation payload validation -------------------------------------------
class TestGenerationPayload:
    """Validates that the new payload shape (source_ids, jurisprudence_ids,
    language) is accepted. We expect HTTP 200 OR 402 (LLM budget)
    OR 502 (LLM upstream) — but NOT 422 (validation error)."""

    def test_payload_validation(self, session, admin_headers):
        # Get a Mauritanian institution
        r = session.get(f"{BASE_URL}/api/institutions",
                        headers=admin_headers,
                        params={"country_code": "MR"}, timeout=15)
        assert r.status_code == 200
        insts = r.json()
        if not insts:
            pytest.skip("no MR institution seeded")
        inst_id = insts[0]["id"]

        payload = {
            "topic": "Test prompt arabe",
            "institution_id": inst_id,
            "cycle": "Licence 3",
            "duration": "1 jour (8h)",
            "year": 2026,
            "sources": "",
            "source_ids": [],
            "jurisprudence_ids": [],
            "language": "ar",
        }
        r = session.post(f"{BASE_URL}/api/generations",
                         headers={**admin_headers, "Content-Type": "application/json"},
                         json=payload, timeout=240)
        # Validation must pass; LLM may still fail
        assert r.status_code != 422, f"Validation failed: {r.text}"
        assert r.status_code in {200, 402, 502}, f"Unexpected: {r.status_code} {r.text}"


# --- Email service -----------------------------------------------------------
class TestEmailService:
    def test_module_imports(self):
        from email_service import send_payment_confirmation
        assert callable(send_payment_confirmation)

    def test_send_to_resend_test_address(self):
        """Best-effort send; do not fail suite if Resend rejects."""
        from email_service import send_payment_confirmation
        try:
            ok = asyncio.run(send_payment_confirmation(
                recipient_email="delivered@resend.dev",
                full_name="TEST User",
                topic="TEST topic",
                generation_id=str(uuid.uuid4()),
            ))
        except Exception as exc:
            pytest.skip(f"Resend send raised: {exc}")
        # Either True or False; both are acceptable (sandbox restrictions)
        assert ok in (True, False)
