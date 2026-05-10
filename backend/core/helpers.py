"""VITA-FORM — helpers partagés (LLM, paywall, payments email)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from emergentintegrations.llm.chat import LlmChat, UserMessage

from email_service import send_payment_confirmation

from .config import EMERGENT_LLM_KEY, LLM_MODEL, PAYWALL_PRICE
from .database import db

logger = logging.getLogger("vitaform")

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
_TRANSIENT_HINTS = ("502", "503", "504", "BadGateway", "ServiceUnavailable",
                    "GatewayTimeout", "overloaded", "rate_limit",
                    "Connection reset", "Connection aborted", "Read timed out",
                    "TimeoutError", "timeout", "InternalServer")


def _classify_llm_error(msg: str) -> str:
    """Return one of: 'budget' | 'transient' | 'unauthorized' | 'unknown'."""
    if "Budget has been exceeded" in msg or "budget_exceeded" in msg:
        return "budget"
    if "401" in msg or "Unauthorized" in msg or "invalid_api_key" in msg:
        return "unauthorized"
    if any(hint in msg for hint in _TRANSIENT_HINTS):
        return "transient"
    return "unknown"


async def call_claude(system_prompt: str, user_text: str, session_id: str,
                      max_retries: int = 2) -> str:
    """Appelle Claude via Emergent + retry sur erreurs transientes (502/503/timeout)."""
    last_msg = ""
    for attempt in range(max_retries + 1):
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_prompt,
        ).with_model(*LLM_MODEL)
        try:
            response = await chat.send_message(UserMessage(text=user_text))
            return response if isinstance(response, str) else str(response)
        except Exception as exc:
            last_msg = str(exc)
            kind = _classify_llm_error(last_msg)
            logger.warning(
                "LLM attempt %d/%d failed (%s): %s",
                attempt + 1, max_retries + 1, kind, last_msg[:300],
            )
            if kind == "budget":
                raise HTTPException(
                    status_code=402,
                    detail=(
                        "Crédit Emergent LLM épuisé. Rendez-vous dans Profile → "
                        "Universal Key → Add Balance pour recharger, puis relancez "
                        "la génération."
                    ),
                )
            if kind == "unauthorized":
                raise HTTPException(
                    status_code=401,
                    detail="Clé Emergent LLM invalide ou expirée — contactez l'administrateur.",
                )
            if kind == "transient" and attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # 1s, 2s
                continue
            # No more retries or unknown error → bubble up
            break

    raise HTTPException(
        status_code=502,
        detail=(
            "Le service IA est temporairement indisponible (proxy Claude saturé "
            "ou en maintenance). Réessayez dans 1 à 2 minutes. Si le problème "
            "persiste, vérifiez le solde Universal Key et l'état du service "
            "Anthropic. Détail technique : "
            f"{last_msg[:180]}"
        ),
    )


async def resolve_sources(user_id: str, payload) -> str:
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
                parts.append(
                    f"### Source utilisateur — {r.get('original_filename','sans nom')}\n{txt}"
                )
    if payload.jurisprudence_ids:
        rows = await db.jurisprudences.find(
            {"id": {"$in": payload.jurisprudence_ids}},
            {"_id": 0, "title": 1, "reference": 1, "body": 1, "country": 1},
        ).to_list(20)
        for r in rows:
            ref = f" ({r.get('reference')})" if r.get("reference") else ""
            parts.append(
                f"### Jurisprudence — {r.get('title')}{ref} · {r.get('country')}\n"
                f"{r.get('body','')}"
            )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Paywall
# ---------------------------------------------------------------------------
def is_unlocked(doc: dict, user: dict) -> bool:
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


def public_generation(doc: dict, user: dict, full: bool = False) -> dict:
    unlocked = is_unlocked(doc, user)
    out = {k: v for k, v in doc.items() if k != "_id"}
    content = out.get("content", "")
    if not unlocked:
        preview = content[:1200]
        if len(content) > 1200:
            preview += "\n\n*...(aperçu tronqué — débloquez le livrable pour la version complète)...*"
        out["content"] = preview
    out["unlocked"] = unlocked
    out["paywall_price_eur"] = PAYWALL_PRICE
    return out


# ---------------------------------------------------------------------------
# Email post-paiement
# ---------------------------------------------------------------------------
async def send_payment_email(generation_id: str, user_email: Optional[str]) -> None:
    if not user_email:
        return
    gen = await db.generations.find_one({"id": generation_id}, {"_id": 0})
    if not gen:
        return
    u = await db.users.find_one(
        {"id": gen["user_id"]}, {"_id": 0, "password_hash": 0}
    )
    full_name = (u or {}).get("full_name", "Apprenant")
    try:
        await send_payment_confirmation(
            recipient_email=user_email,
            full_name=full_name,
            topic=gen.get("topic", "Livrable VITA-FORM"),
            generation_id=generation_id,
        )
    except Exception as exc:
        logger.warning("Email post-paiement échec: %s", exc)
