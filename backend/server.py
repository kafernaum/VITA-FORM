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
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Header, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)
import stripe as stripe_sdk

from seeds import INSTITUTIONS_SEED, CYCLES, DURATIONS, DAILY_SALARIES
from vitalist_corpus import (
    VITALIST_SYSTEM_PROMPT,
    build_course_prompt,
    build_vitalist_analysis_prompt,
)
from exporters import render_pdf, render_docx, render_slides_html


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
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")

# Fixed pricing packages (server-side only, NEVER trust client amounts)
PAYWALL_PACKAGES = {
    "single_deliverable": {"amount": PAYWALL_PRICE, "currency": "eur",
                            "label": "Livrable unique VITA-FORM"},
}

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


class StripeCheckoutIn(BaseModel):
    generation_id: str
    origin_url: str  # window.location.origin from frontend


# ---------------------------------------------------------------------------
# Bootstrap data
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def bootstrap():
    # Seed institutions if empty
    count = await db.institutions.count_documents({})
    if count == 0:
        for it in INSTITUTIONS_SEED:
            await db.institutions.insert_one({**it, "id": str(uuid.uuid4())})
        logger.info("Seeded %d institutions", len(INSTITUTIONS_SEED))

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
        "content": content,
        "kind": "course",
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generations.insert_one(doc.copy())
    return _public_generation(doc, user)


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
# Paiement Stripe (réel — clé test du pod)
# ---------------------------------------------------------------------------
@api.post("/payments/checkout")
async def stripe_create_checkout(payload: StripeCheckoutIn, request: Request,
                                  user: dict = Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe non configuré.")
    doc = await db.generations.find_one({"id": payload.generation_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Livrable introuvable.")
    if doc["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    pkg = PAYWALL_PACKAGES["single_deliverable"]
    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/preview/{payload.generation_id}"

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    metadata = {
        "user_id": user["id"],
        "user_email": user["email"],
        "generation_id": payload.generation_id,
        "package_id": "single_deliverable",
    }
    req = CheckoutSessionRequest(
        amount=pkg["amount"], currency=pkg["currency"],
        success_url=success_url, cancel_url=cancel_url, metadata=metadata,
    )
    try:
        session = await stripe_checkout.create_checkout_session(req)
    except Exception as exc:
        logger.exception("Stripe session creation failed")
        raise HTTPException(status_code=502, detail=f"Échec Stripe : {exc}")

    # Persist payment_transactions row (status = initiated)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "user_email": user["email"],
        "generation_id": payload.generation_id,
        "amount": pkg["amount"],
        "currency": pkg["currency"],
        "metadata": metadata,
        "status": "initiated",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api.get("/payments/checkout/status/{session_id}")
async def stripe_checkout_status(session_id: str, request: Request,
                                  user: dict = Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe non configuré.")

    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable.")
    if txn["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé.")

    # If the webhook has already flipped status to paid, short-circuit.
    if txn.get("payment_status") == "paid":
        return {
            "session_id": session_id,
            "status": txn.get("status", "complete"),
            "payment_status": "paid",
            "amount_total": int(txn.get("amount", 0) * 100),
            "currency": txn.get("currency", "eur"),
            "generation_id": txn["generation_id"],
        }

    # Otherwise, try a fresh Stripe retrieve (best-effort; webhook is source of truth)
    host_url = str(request.base_url)
    StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}api/webhook/stripe")
    new_status = txn.get("status", "open")
    new_payment = txn.get("payment_status", "pending")
    amount_total = int(txn.get("amount", 0) * 100)
    currency = txn.get("currency", "eur")
    try:
        sess = await asyncio.to_thread(
            stripe_sdk.checkout.Session.retrieve, session_id
        )
        new_status = sess.get("status") or new_status
        new_payment = sess.get("payment_status") or new_payment
        amount_total = sess.get("amount_total") or amount_total
        currency = sess.get("currency") or currency
    except Exception as exc:
        # Proxy may temporarily return 404 — webhook will eventually catch it
        logger.warning("Stripe retrieve failed (will rely on webhook): %s", exc)

    update = {
        "status": new_status,
        "payment_status": new_payment,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    if new_payment == "paid" and txn["payment_status"] != "paid":
        await db.generations.update_one(
            {"id": txn["generation_id"]},
            {"$set": {"paid": True, "paid_at": datetime.now(timezone.utc).isoformat(),
                      "payment_session_id": session_id}},
        )

    return {
        "session_id": session_id,
        "status": new_status,
        "payment_status": new_payment,
        "amount_total": amount_total,
        "currency": currency,
        "generation_id": txn["generation_id"],
    }


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    if not STRIPE_API_KEY:
        return {"status": "stripe_disabled"}
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    try:
        event = await stripe_checkout.handle_webhook(body, signature)
    except Exception as exc:
        logger.exception("Stripe webhook failed")
        raise HTTPException(status_code=400, detail=f"Webhook invalide: {exc}")

    if event.session_id:
        txn = await db.payment_transactions.find_one(
            {"session_id": event.session_id}, {"_id": 0})
        if txn and event.payment_status == "paid" and txn["payment_status"] != "paid":
            await db.payment_transactions.update_one(
                {"session_id": event.session_id},
                {"$set": {"payment_status": "paid", "status": "complete",
                          "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            await db.generations.update_one(
                {"id": txn["generation_id"]},
                {"$set": {"paid": True,
                          "paid_at": datetime.now(timezone.utc).isoformat(),
                          "payment_session_id": event.session_id}},
            )
    return {"received": True, "event_type": event.event_type}


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
