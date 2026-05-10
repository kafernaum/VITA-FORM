"""VITA-FORM — Service LLM multi-provider.

Permet à l'admin de configurer ses propres clés API (Anthropic / OpenAI / Google)
depuis l'interface. Emergent LLM reste en fallback si aucun provider n'est actif.

Modèles par défaut (peuvent être surchargés par provider config) :
- anthropic : claude-sonnet-4-5-20250929
- openai    : gpt-4o
- google    : gemini-2.5-pro
- emergent  : claude-sonnet-4-5 (via litellm)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import HTTPException

from .config import EMERGENT_LLM_KEY
from .database import db

logger = logging.getLogger("vitaform")

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "openai": "gpt-4o",
    "google": "gemini-2.5-pro",
    "emergent": "claude-sonnet-4-5-20250929",
}

SUPPORTED_PROVIDERS = list(DEFAULT_MODELS.keys())


async def get_active_provider() -> dict:
    """Retourne le provider actif (is_default=True et active=True) ou Emergent fallback."""
    doc = await db.llm_providers.find_one(
        {"is_default": True, "active": True}, {"_id": 0},
    )
    if doc:
        return doc
    # Fallback Emergent
    if EMERGENT_LLM_KEY:
        return {
            "id": "emergent-fallback",
            "provider": "emergent",
            "api_key": EMERGENT_LLM_KEY,
            "model": DEFAULT_MODELS["emergent"],
            "is_default": True,
            "active": True,
        }
    raise HTTPException(
        status_code=503,
        detail=(
            "Aucun moteur IA configuré. L'administrateur doit ajouter une clé API "
            "(Anthropic / OpenAI / Google) dans /admin → Moteurs IA."
        ),
    )


def _classify_error(msg: str) -> str:
    msg_lower = msg.lower()
    if "budget" in msg_lower or "insufficient_quota" in msg_lower or "exceeded" in msg_lower:
        return "budget"
    if "401" in msg or "unauthorized" in msg_lower or "invalid_api_key" in msg_lower \
       or "api key" in msg_lower:
        return "unauthorized"
    if any(h in msg for h in ("502", "503", "504", "BadGateway", "ServiceUnavailable",
                              "GatewayTimeout", "overloaded", "rate_limit",
                              "Connection reset", "Read timed out", "timeout")):
        return "transient"
    return "unknown"


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------
async def _call_anthropic(api_key: str, model: str, system: str,
                          user: str, max_tokens: int = 8000) -> str:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)
    msg = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Extract text from content blocks
    parts = []
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


async def _call_openai(api_key: str, model: str, system: str,
                       user: str, max_tokens: int = 8000) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        max_completion_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


async def _call_google(api_key: str, model: str, system: str, user: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    resp = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=user,
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return (resp.text or "").strip()


async def _call_emergent(api_key: str, model: str, system: str,
                         user: str, session_id: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=api_key, session_id=session_id, system_message=system,
    ).with_model("anthropic", model)
    response = await chat.send_message(UserMessage(text=user))
    return response if isinstance(response, str) else str(response)


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------
async def call_llm(system_prompt: str, user_text: str, session_id: str,
                   max_retries: int = 1, provider_override: Optional[dict] = None,
                   ) -> dict:
    """Appelle le LLM avec retry sur erreurs transientes.

    Retourne {'content': str, 'provider': str, 'model': str}.
    Lève HTTPException si échec final.
    """
    provider_doc = provider_override or await get_active_provider()
    provider = provider_doc["provider"]
    api_key = provider_doc["api_key"]
    model = provider_doc.get("model") or DEFAULT_MODELS[provider]

    last_msg = ""
    for attempt in range(max_retries + 1):
        try:
            if provider == "anthropic":
                content = await _call_anthropic(api_key, model, system_prompt, user_text)
            elif provider == "openai":
                content = await _call_openai(api_key, model, system_prompt, user_text)
            elif provider == "google":
                content = await _call_google(api_key, model, system_prompt, user_text)
            elif provider == "emergent":
                content = await _call_emergent(api_key, model, system_prompt,
                                               user_text, session_id)
            else:
                raise HTTPException(status_code=500, detail=f"Provider inconnu: {provider}")

            if not content or len(content.strip()) < 20:
                raise RuntimeError("Réponse vide ou trop courte du moteur IA.")
            return {"content": content, "provider": provider, "model": model}

        except HTTPException:
            raise
        except Exception as exc:
            last_msg = str(exc)
            kind = _classify_error(last_msg)
            logger.warning(
                "LLM[%s/%s] attempt %d/%d failed (%s): %s",
                provider, model, attempt + 1, max_retries + 1, kind, last_msg[:300],
            )
            if kind == "budget":
                raise HTTPException(
                    status_code=402,
                    detail=(
                        f"Crédit/quota épuisé pour le provider « {provider} ». "
                        "Rechargez votre compte chez le provider ou changez de "
                        "moteur IA actif dans /admin → Moteurs IA."
                    ),
                )
            if kind == "unauthorized":
                raise HTTPException(
                    status_code=401,
                    detail=(
                        f"Clé API invalide pour « {provider} ». "
                        "Mettez à jour la clé dans /admin → Moteurs IA."
                    ),
                )
            if kind == "transient" and attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            break

    raise HTTPException(
        status_code=502,
        detail=(
            f"Le moteur IA « {provider} » est temporairement indisponible. "
            f"Détail technique : {last_msg[:200]}"
        ),
    )
