"""VITA-FORM — Backend FastAPI.

Stack: FastAPI + Motor (MongoDB) + Claude Sonnet 4.5 (via emergentintegrations)
       + ReportLab + python-docx pour les exports.
"""
from __future__ import annotations

import io
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Literal

import bcrypt
import jwt
import asyncio
from fastapi import (
    FastAPI, APIRouter, HTTPException, Depends, status, Header, Request,
    UploadFile, File, Query,
)
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage

from seeds import INSTITUTIONS_SEED, CYCLES, DURATIONS, DAILY_SALARIES
from jurisprudence_seed import JURISPRUDENCES_SEED
from vitalist_corpus import (
    VITALIST_SYSTEM_PROMPT,
    build_course_prompt,
    build_vitalist_analysis_prompt,
)
from exporters import render_pdf, render_docx, render_slides_html
from storage_client import init_storage, put_object, APP_NAME
from sources_extractor import extract as extract_source
from email_service import send_payment_confirmation
from paypal_service import (
    build_checkout_url as paypal_build_checkout_url,
    verify_ipn as paypal_verify_ipn,
    is_payment_acceptable as paypal_is_payment_acceptable,
    SUPPORTED_CURRENCIES as PAYPAL_CURRENCIES,
    PRICE_BY_CURRENCY as PAYPAL_PRICES,
    get_business_email as paypal_business_email,
)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "vitaform-secret")
JWT_ALG = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXP_HOURS = 24 * 7
PAYWALL_PRICE = float(os.environ.get("PAYWALL_PRICE_EUR", "14.90"))

LLM_MODEL = ("anthropic", "claude-sonnet-4-5-20250929")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("vitaform")

app = FastAPI(title="VITA-FORM API", version="1.0.0")
api = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Helpers — Auth
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    return user


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    user: dict


class GenerationCreate(BaseModel):
    topic: str = Field(min_length=4)
    institution_id: str
    cycle: str
    duration: str
    year: int = Field(default_factory=lambda: datetime.now().year)
    sources: Optional[str] = ""
    source_ids: Optional[List[str]] = None  # uploaded source IDs to inline
    jurisprudence_ids: Optional[List[str]] = None  # corpus refs to inline
    language: Literal["fr", "ar"] = "fr"


class VitalistAnalyzeIn(BaseModel):
    document_type: Literal[
        "Budget", "Convention de prêt", "Bilan", "Loi de finances",
        "Marché public", "Dette publique", "Autre"
    ]
    document_text: str = Field(min_length=20)
    monetary_amount: float = Field(gt=0)
    country_code: str = Field(default="FR")
    daily_salary: Optional[float] = None
    title: str = Field(default="Analyse vitaliste")


class InstitutionIn(BaseModel):
    name: str
    country: str
    country_code: str
    city: str
    type: str


class JurisprudenceIn(BaseModel):
    title: str = Field(min_length=3)
    country: str
    body: str = Field(min_length=20)
    reference: Optional[str] = ""
    tags: Optional[List[str]] = None


class PayPalCheckoutIn(BaseModel):
    generation_id: str
    origin_url: str
    currency: str = "EUR"


# ---------------------------------------------------------------------------
# Bootstrap data
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def bootstrap():
    # Init Emergent object storage
    try:
        init_storage()
    except Exception as exc:
        logger.warning("Storage init failed: %s", exc)

    # Seed institutions if empty
    count = await db.institutions.count_documents({})
    if count == 0:
        for it in INSTITUTIONS_SEED:
            await db.institutions.insert_one({**it, "id": str(uuid.uuid4())})
        logger.info("Seeded %d institutions", len(INSTITUTIONS_SEED))

    # Ensure text index for jurisprudence search
    try:
        await db.jurisprudences.create_index(
            [("title", "text"), ("body", "text"), ("reference", "text")],
            default_language="french",
        )
    except Exception as exc:
        logger.warning("Jurisprudence text index: %s", exc)

    # Seed jurisprudence corpus once
    if await db.jurisprudences.count_documents({}) == 0:
        for j in JURISPRUDENCES_SEED:
            await db.jurisprudences.insert_one({
                "id": str(uuid.uuid4()),
                **j,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.info("Seeded %d jurisprudences", len(JURISPRUDENCES_SEED))

    # Ensure default admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@vita-form.com")
    admin_pw = os.environ.get("ADMIN_PASSWORD", "VitaForm2026!Admin")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "full_name": "Administrateur VITA-FORM",
            "password_hash": hash_password(admin_pw),
            "role": "admin",
            "vip": True,
            "vip_until": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Seeded admin %s", admin_email)


# ---------------------------------------------------------------------------
# Routes — Public / Auth
# ---------------------------------------------------------------------------
@api.get("/")
async def root():
    return {"app": "VITA-FORM", "status": "ok", "version": "1.0.0"}


@api.post("/auth/register", response_model=TokenOut)
async def register(payload: RegisterIn):
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Cet e-mail est déjà inscrit.")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": payload.email.lower(),
        "full_name": payload.full_name,
        "password_hash": hash_password(payload.password),
        "role": "user",
        "vip": False,
        "vip_until": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_token(user_id, "user")
    return TokenOut(access_token=token, user={
        "id": user_id, "email": doc["email"], "full_name": doc["full_name"],
        "role": "user", "vip": False,
    })


@api.post("/auth/login", response_model=TokenOut)
async def login(payload: LoginIn):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    token = create_token(user["id"], user.get("role", "user"))
    return TokenOut(access_token=token, user={
        "id": user["id"], "email": user["email"], "full_name": user["full_name"],
        "role": user.get("role", "user"), "vip": user.get("vip", False),
    })


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------------------
# Routes — Institutions & meta
# ---------------------------------------------------------------------------
@api.get("/meta/options")
async def meta_options():
    return {"cycles": CYCLES, "durations": DURATIONS, "daily_salaries": DAILY_SALARIES}


@api.get("/institutions")
async def list_institutions(country_code: Optional[str] = None):
    query = {}
    if country_code:
        query["country_code"] = country_code.upper()
    items = await db.institutions.find(query, {"_id": 0}).sort("country", 1).to_list(500)
    return items


# ---------------------------------------------------------------------------
# Routes — Génération de cours
# ---------------------------------------------------------------------------
async def _call_claude(system_prompt: str, user_text: str, session_id: str) -> str:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model(*LLM_MODEL)
    try:
        response = await chat.send_message(UserMessage(text=user_text))
    except Exception as exc:
        msg = str(exc)
        if "Budget has been exceeded" in msg or "budget_exceeded" in msg:
            raise HTTPException(
                status_code=402,
                detail="Crédit Emergent LLM épuisé. Rendez-vous dans Profile → Universal Key → Add Balance pour recharger, puis relancez la génération.",
            )
        raise HTTPException(status_code=502, detail=f"Erreur du moteur IA: {msg[:200]}")
    return response if isinstance(response, str) else str(response)


@api.post("/generations")
async def create_generation(payload: GenerationCreate, user: dict = Depends(get_current_user)):
    institution = await db.institutions.find_one({"id": payload.institution_id}, {"_id": 0})
    if not institution:
        raise HTTPException(status_code=404, detail="Institution introuvable.")

    user_prompt = build_course_prompt(
        topic=payload.topic,
        institution=institution["name"],
        country=institution["country"],
        cycle=payload.cycle,
        duration=payload.duration,
        year=payload.year,
        sources=payload.sources or "",
    )
    gen_id = str(uuid.uuid4())
    try:
        content = await _call_claude(
            VITALIST_SYSTEM_PROMPT, user_prompt, session_id=f"gen-{gen_id}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Claude generation failed")
        raise HTTPException(status_code=502, detail=f"Erreur du moteur IA: {exc}")

    doc = {
        "id": gen_id,
        "user_id": user["id"],
        "topic": payload.topic,
        "institution_id": payload.institution_id,
        "institution_name": institution["name"],
        "country": institution["country"],
        "cycle": payload.cycle,
        "duration": payload.duration,
        "year": payload.year,
        "language": payload.language,
        "content": content,
        "kind": "course",
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generations.insert_one(doc.copy())
    return _public_generation(doc, user)


async def _resolve_sources(user_id: str, payload: "GenerationCreate") -> str:
    """Concat sources from user uploads + jurisprudences + free text."""
    parts: list[str] = []
    if payload.sources:
        parts.append(payload.sources.strip())
    if payload.source_ids:
        rows = await db.sources.find(
            {"id": {"$in": payload.source_ids}, "user_id": user_id, "is_deleted": False},
            {"_id": 0, "extracted_text": 1, "original_filename": 1},
        ).to_list(20)
        for r in rows:
            txt = (r.get("extracted_text") or "").strip()
            if txt:
                parts.append(f"### Source utilisateur — {r.get('original_filename','sans nom')}\n{txt}")
    if payload.jurisprudence_ids:
        rows = await db.jurisprudences.find(
            {"id": {"$in": payload.jurisprudence_ids}},
            {"_id": 0, "title": 1, "reference": 1, "body": 1, "country": 1},
        ).to_list(20)
        for r in rows:
            ref = f" ({r.get('reference')})" if r.get('reference') else ""
            parts.append(f"### Jurisprudence — {r.get('title')}{ref} · {r.get('country')}\n{r.get('body','')}")
    return "\n\n".join(parts)


@api.post("/vitalist/analyze")
async def analyze_vitalist(payload: VitalistAnalyzeIn, user: dict = Depends(get_current_user)):
    salary_meta = DAILY_SALARIES.get(payload.country_code.upper(), DAILY_SALARIES["FR"])
    daily = payload.daily_salary or salary_meta["value"]
    country_label = salary_meta["label"]

    # Calculs vitalistes (locaux)
    days = payload.monetary_amount / daily if daily > 0 else 0
    years = days / 365.25
    months = days / 30.44

    user_prompt = build_vitalist_analysis_prompt(
        document_type=payload.document_type,
        document_text=payload.document_text,
        monetary_amount=payload.monetary_amount,
        country=country_label,
        daily_salary=daily,
    )
    gen_id = str(uuid.uuid4())
    try:
        content = await _call_claude(
            VITALIST_SYSTEM_PROMPT, user_prompt, session_id=f"vit-{gen_id}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Vitalist analysis failed")
        raise HTTPException(status_code=502, detail=f"Erreur du moteur IA: {exc}")

    metrics = {
        "monetary_amount": payload.monetary_amount,
        "currency": salary_meta["currency"],
        "daily_salary": daily,
        "life_days": round(days, 2),
        "life_months": round(months, 2),
        "life_years": round(years, 3),
    }

    doc = {
        "id": gen_id,
        "user_id": user["id"],
        "topic": payload.title,
        "institution_id": None,
        "institution_name": "Analyse Vitaliste Pratique",
        "country": country_label,
        "cycle": payload.document_type,
        "duration": "Rapport unique",
        "year": datetime.now().year,
        "content": content,
        "kind": "vitalist_analysis",
        "metrics": metrics,
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generations.insert_one(doc.copy())
    out = _public_generation(doc, user)
    out["metrics"] = metrics
    return out


@api.get("/generations")
async def list_my_generations(user: dict = Depends(get_current_user)):
    items = await db.generations.find(
        {"user_id": user["id"]}, {"_id": 0, "content": 0}
    ).sort("created_at", -1).to_list(200)
    for it in items:
        it["unlocked"] = _is_unlocked(it, user)
    return items


@api.get("/generations/{gen_id}")
async def get_generation(gen_id: str, user: dict = Depends(get_current_user)):
    doc = await db.generations.find_one({"id": gen_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Livrable introuvable.")
    if doc["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé.")
    return _public_generation(doc, user, full=True)


def _is_unlocked(doc: dict, user: dict) -> bool:
    if doc.get("paid"):
        return True
    if user.get("role") == "admin":
        return True
    if user.get("vip"):
        until = user.get("vip_until")
        if not until:
            return True
        try:
            return datetime.fromisoformat(until) > datetime.now(timezone.utc)
        except Exception:
            return True
    return False


def _public_generation(doc: dict, user: dict, full: bool = False) -> dict:
    unlocked = _is_unlocked(doc, user)
    out = {k: v for k, v in doc.items() if k != "_id"}
    content = out.get("content", "")
    if not unlocked:
        # Tronquer à ~1200 caractères + watermark
        preview = content[:1200]
        if len(content) > 1200:
            preview += "\n\n*...(aperçu tronqué — débloquez le livrable pour la version complète)...*"
        out["content"] = preview
    out["unlocked"] = unlocked
    out["paywall_price_eur"] = PAYWALL_PRICE
    return out


# ---------------------------------------------------------------------------
# Téléchargement (paywall hermétique)
# ---------------------------------------------------------------------------
@api.get("/generations/{gen_id}/download/{fmt}")
async def download_generation(
    gen_id: str,
    fmt: Literal["pdf", "docx", "slides"],
    user: dict = Depends(get_current_user),
):
    doc = await db.generations.find_one({"id": gen_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Livrable introuvable.")
    if doc["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé.")
    if not _is_unlocked(doc, user):
        raise HTTPException(status_code=402, detail="Paiement requis pour télécharger.")

    title = doc.get("topic", "Livrable VITA-FORM")
    institution = doc.get("institution_name", "")
    author_name = user.get("full_name", "Apprenant")
    content = doc.get("content", "")

    if fmt == "pdf":
        data = render_pdf(title, author_name, institution, content)
        media = "application/pdf"
        ext = "pdf"
    elif fmt == "docx":
        data = render_docx(title, author_name, institution, content)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        data = render_slides_html(title, author_name, institution, content)
        media = "text/html"
        ext = "html"

    filename = f"vitaform-{gen_id[:8]}.{ext}"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Paiement PayPal (compte personnel/business standard, flux _xclick)
# ---------------------------------------------------------------------------
@api.get("/payments/options")
async def payment_options():
    """Devises supportées + grille tarifaire."""
    return {
        "currencies": PAYPAL_CURRENCIES,
        "prices": PAYPAL_PRICES,
        "default_currency": "EUR",
        "merchant_email": paypal_business_email(),
    }


@api.post("/payments/checkout")
async def paypal_create_checkout(payload: PayPalCheckoutIn,
                                  user: dict = Depends(get_current_user)):
    if not paypal_business_email():
        raise HTTPException(status_code=500, detail="PayPal non configuré.")
    currency = payload.currency.upper()
    if currency not in PAYPAL_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Devise non supportée : {currency}")

    doc = await db.generations.find_one({"id": payload.generation_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Livrable introuvable.")
    if doc["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    amount = PAYPAL_PRICES.get(currency, PAYWALL_PRICE)
    txn_id = str(uuid.uuid4())
    origin = payload.origin_url.rstrip("/")
    return_url = f"{origin}/payment/success?txn_id={txn_id}"
    cancel_url = f"{origin}/preview/{payload.generation_id}"
    # Public URL is required for PayPal IPN (preview/prod)
    notify_url = f"{os.environ.get('PUBLIC_APP_URL', origin)}/api/webhook/paypal"

    item_name = f"VITA-FORM — Livrable « {doc.get('topic','')[:90]} »"

    try:
        url = paypal_build_checkout_url(
            txn_id=txn_id, item_name=item_name, amount=amount,
            currency=currency, return_url=return_url,
            cancel_url=cancel_url, notify_url=notify_url,
        )
    except Exception as exc:
        logger.exception("PayPal URL build failed")
        raise HTTPException(status_code=502, detail=f"Échec PayPal : {exc}")

    await db.payment_transactions.insert_one({
        "id": txn_id,
        "session_id": txn_id,  # alias pour compat ascendante
        "provider": "paypal",
        "user_id": user["id"],
        "user_email": user["email"],
        "generation_id": payload.generation_id,
        "amount": amount,
        "currency": currency,
        "status": "initiated",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": url, "txn_id": txn_id, "amount": amount, "currency": currency}


@api.get("/payments/checkout/status/{txn_id}")
async def paypal_checkout_status(txn_id: str,
                                  user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable.")
    if txn["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé.")
    return {
        "txn_id": txn_id,
        "session_id": txn_id,
        "status": txn.get("status", "initiated"),
        "payment_status": txn.get("payment_status", "pending"),
        "amount": txn.get("amount"),
        "currency": txn.get("currency"),
        "generation_id": txn["generation_id"],
    }


async def _send_payment_email(generation_id: str, user_email: Optional[str]) -> None:
    if not user_email:
        return
    gen = await db.generations.find_one({"id": generation_id}, {"_id": 0})
    if not gen:
        return
    u = await db.users.find_one({"id": gen["user_id"]}, {"_id": 0, "password_hash": 0})
    full_name = (u or {}).get("full_name", "Apprenant")
    try:
        await send_payment_confirmation(
            recipient_email=user_email, full_name=full_name,
            topic=gen.get("topic", "Livrable VITA-FORM"),
            generation_id=generation_id,
        )
    except Exception as exc:
        logger.warning("Email post-paiement échec: %s", exc)


@api.post("/webhook/paypal")
async def paypal_ipn_webhook(request: Request):
    """Reçoit l'IPN PayPal, le vérifie, déverrouille le livrable."""
    raw = await request.body()
    if not raw:
        return {"status": "empty"}

    # Parse form-urlencoded payload
    from urllib.parse import parse_qs
    parsed = parse_qs(raw.decode("utf-8", errors="ignore"), keep_blank_values=True)
    ipn = {k: (v[0] if v else "") for k, v in parsed.items()}

    txn_id = ipn.get("custom") or ipn.get("item_number")
    if not txn_id:
        logger.warning("IPN sans custom/item_number")
        return {"status": "ignored"}

    # 1. Vérification chez PayPal (anti-spoof)
    verified = await asyncio.to_thread(paypal_verify_ipn, raw)
    if not verified:
        logger.warning("IPN PayPal NON vérifié pour txn=%s", txn_id)
        return {"status": "invalid"}

    txn = await db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        logger.warning("IPN reçu pour txn inconnu: %s", txn_id)
        return {"status": "unknown_txn"}

    # 2. Idempotence
    if txn.get("payment_status") == "paid":
        return {"status": "already_processed"}

    # 3. Contrôles métier (montant, devise, destinataire)
    ok, reason = paypal_is_payment_acceptable(
        ipn,
        expected_amount=float(txn.get("amount", 0)),
        expected_currency=txn.get("currency", "EUR"),
    )

    update = {
        "ipn_payload": ipn,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not ok:
        update["status"] = "rejected"
        update["rejection_reason"] = reason
        await db.payment_transactions.update_one({"id": txn_id}, {"$set": update})
        logger.warning("IPN rejeté txn=%s reason=%s", txn_id, reason)
        return {"status": "rejected", "reason": reason}

    # 4. Déverrouillage idempotent
    update["status"] = "complete"
    update["payment_status"] = "paid"
    update["paypal_txn_id"] = ipn.get("txn_id", "")
    await db.payment_transactions.update_one({"id": txn_id}, {"$set": update})

    await db.generations.update_one(
        {"id": txn["generation_id"]},
        {"$set": {"paid": True,
                  "paid_at": datetime.now(timezone.utc).isoformat(),
                  "payment_txn_id": txn_id}},
    )
    await _send_payment_email(txn["generation_id"], txn.get("user_email"))
    logger.info("PayPal IPN OK : livrable %s déverrouillé", txn["generation_id"])
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@api.get("/admin/users")
async def admin_users(_: dict = Depends(require_admin)):
    items = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    # enrichir avec stats
    for it in items:
        it["generations_count"] = await db.generations.count_documents({"user_id": it["id"]})
        it["payments_count"] = await db.payment_transactions.count_documents(
            {"user_id": it["id"], "payment_status": "paid"})
    return items


@api.post("/admin/users/{user_id}/vip")
async def admin_set_vip(user_id: str, vip: bool = True, days: Optional[int] = None,
                        _: dict = Depends(require_admin)):
    update = {"vip": vip}
    if vip and days:
        update["vip_until"] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    elif vip:
        update["vip_until"] = None
    else:
        update["vip_until"] = None
    res = await db.users.update_one({"id": user_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    return {"status": "ok", "vip": vip, "until": update.get("vip_until")}


@api.get("/admin/stats")
async def admin_stats(_: dict = Depends(require_admin)):
    return {
        "users": await db.users.count_documents({}),
        "generations": await db.generations.count_documents({}),
        "payments": await db.payment_transactions.count_documents({"payment_status": "paid"}),
        "institutions": await db.institutions.count_documents({}),
    }


@api.get("/admin/generations")
async def admin_generations(_: dict = Depends(require_admin)):
    items = await db.generations.find({}, {"_id": 0, "content": 0}).sort(
        "created_at", -1).to_list(500)
    return items


@api.post("/admin/institutions")
async def admin_create_institution(payload: InstitutionIn, _: dict = Depends(require_admin)):
    doc = {**payload.model_dump(), "id": str(uuid.uuid4())}
    await db.institutions.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@api.delete("/admin/institutions/{inst_id}")
async def admin_delete_institution(inst_id: str, _: dict = Depends(require_admin)):
    res = await db.institutions.delete_one({"id": inst_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Institution introuvable.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Sources upload (PDF / DOCX / TXT) — extraction texte pour le RAG
# ---------------------------------------------------------------------------
ALLOWED_EXT = {"pdf", "docx", "txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@api.post("/sources/upload")
async def upload_source(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    name = file.filename or "source.bin"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400,
                            detail="Format non supporté. Utilisez PDF, DOCX ou TXT.")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (10 Mo max).")

    storage_path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ext}"
    try:
        result = await asyncio.to_thread(
            put_object, storage_path, data,
            file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        logger.exception("Storage upload failed")
        raise HTTPException(status_code=502, detail=f"Échec stockage: {exc}")

    extracted = await asyncio.to_thread(extract_source, name, file.content_type, data)

    src_id = str(uuid.uuid4())
    doc = {
        "id": src_id,
        "user_id": user["id"],
        "storage_path": result["path"],
        "original_filename": name,
        "content_type": file.content_type or "application/octet-stream",
        "size": result.get("size", len(data)),
        "extracted_text": extracted,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.sources.insert_one(doc.copy())
    return {
        "id": src_id,
        "original_filename": name,
        "size": doc["size"],
        "extracted_chars": len(extracted),
        "preview": extracted[:400],
    }


@api.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    rows = await db.sources.find(
        {"user_id": user["id"], "is_deleted": False},
        {"_id": 0, "extracted_text": 0, "storage_path": 0},
    ).sort("created_at", -1).to_list(200)
    return rows


@api.delete("/sources/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(get_current_user)):
    res = await db.sources.update_one(
        {"id": source_id, "user_id": user["id"]},
        {"$set": {"is_deleted": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source introuvable.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Jurisprudences (RAG juridique) — recherche full-text MongoDB
# ---------------------------------------------------------------------------
@api.get("/jurisprudences")
async def search_jurisprudences(q: Optional[str] = Query(None),
                                 country: Optional[str] = Query(None),
                                 limit: int = Query(20, ge=1, le=100),
                                 _: dict = Depends(get_current_user)):
    query: dict = {}
    if country:
        query["country"] = country
    projection = {"_id": 0, "body": 0}
    if q:
        try:
            query["$text"] = {"$search": q}
            projection["score"] = {"$meta": "textScore"}
            cursor = db.jurisprudences.find(query, projection).sort(
                [("score", {"$meta": "textScore"})]).limit(limit)
        except Exception:
            # Fallback regex if text index unavailable
            del query["$text"]
            query["$or"] = [{"title": {"$regex": q, "$options": "i"}},
                            {"body": {"$regex": q, "$options": "i"}}]
            cursor = db.jurisprudences.find(query, projection).limit(limit)
    else:
        cursor = db.jurisprudences.find(query, projection).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(limit)
    return items


@api.get("/jurisprudences/{jur_id}")
async def get_jurisprudence(jur_id: str, _: dict = Depends(get_current_user)):
    doc = await db.jurisprudences.find_one({"id": jur_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Jurisprudence introuvable.")
    return doc


@api.post("/admin/jurisprudences")
async def admin_create_jurisprudence(payload: JurisprudenceIn,
                                      _: dict = Depends(require_admin)):
    doc = {
        "id": str(uuid.uuid4()),
        **payload.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.jurisprudences.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@api.delete("/admin/jurisprudences/{jur_id}")
async def admin_delete_jurisprudence(jur_id: str, _: dict = Depends(require_admin)):
    res = await db.jurisprudences.delete_one({"id": jur_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Jurisprudence introuvable.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Mount
# ---------------------------------------------------------------------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
