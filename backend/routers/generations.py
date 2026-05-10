"""VITA-FORM — Génération de cours + analyse vitaliste + téléchargement (paywall)."""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.database import db
from core.helpers import call_claude, is_unlocked, public_generation
from core.models import GenerationCreate, VitalistAnalyzeIn
from core.security import get_current_user
from exporters import render_docx, render_pdf, render_slides_html
from seeds import DAILY_SALARIES
from vitalist_corpus import (
    VITALIST_SYSTEM_PROMPT,
    build_course_prompt,
    build_vitalist_analysis_prompt,
)

logger = logging.getLogger("vitaform")

router = APIRouter(tags=["generations"])


@router.post("/generations")
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
        language=payload.language,
    )
    gen_id = str(uuid.uuid4())
    try:
        content = await call_claude(
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
    return public_generation(doc, user)


@router.post("/vitalist/analyze")
async def analyze_vitalist(payload: VitalistAnalyzeIn, user: dict = Depends(get_current_user)):
    salary_meta = DAILY_SALARIES.get(payload.country_code.upper(), DAILY_SALARIES["FR"])
    daily = payload.daily_salary or salary_meta["value"]
    country_label = salary_meta["label"]

    days = payload.monetary_amount / daily if daily > 0 else 0
    years = days / 365.25
    months = days / 30.44

    user_prompt = build_vitalist_analysis_prompt(
        document_type=payload.document_type,
        document_text=payload.document_text,
        monetary_amount=payload.monetary_amount,
        country=country_label,
        daily_salary=daily,
        language=payload.language,
    )
    gen_id = str(uuid.uuid4())
    try:
        content = await call_claude(
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
        "language": payload.language,
        "content": content,
        "kind": "vitalist_analysis",
        "metrics": metrics,
        "paid": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.generations.insert_one(doc.copy())
    out = public_generation(doc, user)
    out["metrics"] = metrics
    return out


@router.get("/generations")
async def list_my_generations(user: dict = Depends(get_current_user)):
    items = await db.generations.find(
        {"user_id": user["id"]}, {"_id": 0, "content": 0}
    ).sort("created_at", -1).to_list(200)
    for it in items:
        it["unlocked"] = is_unlocked(it, user)
    return items


@router.get("/generations/{gen_id}")
async def get_generation(gen_id: str, user: dict = Depends(get_current_user)):
    doc = await db.generations.find_one({"id": gen_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Livrable introuvable.")
    if doc["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé.")
    return public_generation(doc, user, full=True)


@router.get("/generations/{gen_id}/download/{fmt}")
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
    if not is_unlocked(doc, user):
        raise HTTPException(status_code=402, detail="Paiement requis pour télécharger.")

    title = doc.get("topic", "Livrable VITA-FORM")
    institution = doc.get("institution_name", "")
    author_name = user.get("full_name", "Apprenant")
    content = doc.get("content", "")
    language = doc.get("language", "fr")

    if fmt == "pdf":
        data = render_pdf(title, author_name, institution, content, language=language)
        media = "application/pdf"
        ext = "pdf"
    elif fmt == "docx":
        data = render_docx(title, author_name, institution, content, language=language)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        data = render_slides_html(title, author_name, institution, content, language=language)
        media = "text/html"
        ext = "html"

    filename = f"vitaform-{gen_id[:8]}.{ext}"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
