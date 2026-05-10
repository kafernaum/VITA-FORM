"""VITA-FORM — Paiements PayPal + virements bancaires (côté utilisateur)."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request

from core.config import PAYWALL_PRICE
from core.database import db
from core.helpers import send_payment_email
from core.models import PayPalCheckoutIn, WireConfirmIn, WireInitiateIn
from core.security import get_current_user
from paypal_service import (
    PRICE_BY_CURRENCY as PAYPAL_PRICES,
    SUPPORTED_CURRENCIES as PAYPAL_CURRENCIES,
    build_checkout_url as paypal_build_checkout_url,
    get_business_email as paypal_business_email,
    is_payment_acceptable as paypal_is_payment_acceptable,
    verify_ipn as paypal_verify_ipn,
)

logger = logging.getLogger("vitaform")

router = APIRouter(tags=["payments"])


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
@router.get("/payments/options")
async def payment_options():
    return {
        "currencies": PAYPAL_CURRENCIES,
        "prices": PAYPAL_PRICES,
        "default_currency": "EUR",
        "merchant_email": paypal_business_email(),
    }


# ---------------------------------------------------------------------------
# PayPal
# ---------------------------------------------------------------------------
@router.post("/payments/checkout")
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
        "session_id": txn_id,
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


@router.get("/payments/checkout/status/{txn_id}")
async def paypal_checkout_status(txn_id: str, user: dict = Depends(get_current_user)):
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


@router.post("/webhook/paypal")
async def paypal_ipn_webhook(request: Request):
    """Reçoit l'IPN PayPal, le vérifie, déverrouille le livrable."""
    raw = await request.body()
    if not raw:
        return {"status": "empty"}

    parsed = parse_qs(raw.decode("utf-8", errors="ignore"), keep_blank_values=True)
    ipn = {k: (v[0] if v else "") for k, v in parsed.items()}

    txn_id = ipn.get("custom") or ipn.get("item_number")
    if not txn_id:
        logger.warning("IPN sans custom/item_number")
        return {"status": "ignored"}

    verified = await asyncio.to_thread(paypal_verify_ipn, raw)
    if not verified:
        logger.warning("IPN PayPal NON vérifié pour txn=%s", txn_id)
        return {"status": "invalid"}

    txn = await db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        logger.warning("IPN reçu pour txn inconnu: %s", txn_id)
        return {"status": "unknown_txn"}

    if txn.get("payment_status") == "paid":
        return {"status": "already_processed"}

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

    update["status"] = "complete"
    update["payment_status"] = "paid"
    update["paypal_txn_id"] = ipn.get("txn_id", "")
    await db.payment_transactions.update_one({"id": txn_id}, {"$set": update})

    await db.generations.update_one(
        {"id": txn["generation_id"]},
        {"$set": {
            "paid": True,
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "payment_txn_id": txn_id,
        }},
    )
    await send_payment_email(txn["generation_id"], txn.get("user_email"))
    logger.info("PayPal IPN OK : livrable %s déverrouillé", txn["generation_id"])
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Wire transfer (utilisateur)
# ---------------------------------------------------------------------------
@router.get("/bank-accounts")
async def list_active_bank_accounts(_: dict = Depends(get_current_user)):
    items = await db.bank_accounts.find(
        {"is_active": True}, {"_id": 0},
    ).sort("currency", 1).to_list(50)
    return items


@router.post("/payments/wire/initiate")
async def wire_initiate(payload: WireInitiateIn, user: dict = Depends(get_current_user)):
    gen = await db.generations.find_one({"id": payload.generation_id}, {"_id": 0})
    if not gen:
        raise HTTPException(status_code=404, detail="Livrable introuvable.")
    if gen["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    bank = await db.bank_accounts.find_one(
        {"id": payload.bank_account_id, "is_active": True}, {"_id": 0})
    if not bank:
        raise HTTPException(status_code=404, detail="Compte bancaire indisponible.")

    currency = payload.currency.upper()
    if currency not in PAYPAL_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Devise non supportée : {currency}")
    amount = PAYPAL_PRICES[currency]
    txn_id = str(uuid.uuid4())
    short_ref = f"VF-{txn_id[:8].upper()}"

    await db.payment_transactions.insert_one({
        "id": txn_id,
        "session_id": txn_id,
        "provider": "wire",
        "method": "wire",
        "user_id": user["id"],
        "user_email": user["email"],
        "generation_id": payload.generation_id,
        "amount": amount,
        "currency": currency,
        "bank_account_id": payload.bank_account_id,
        "wire_reference": short_ref,
        "status": "awaiting_wire",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "txn_id": txn_id,
        "wire_reference": short_ref,
        "amount": amount,
        "currency": currency,
        "bank_account": bank,
        "instructions": (
            f"Virement à effectuer pour {amount:.2f} {currency} "
            f"sur le compte ci-dessus en mentionnant impérativement la référence "
            f"{short_ref} dans le libellé. Une fois le virement émis, "
            "confirmez-le ici pour que l'administrateur valide votre déblocage."
        ),
    }


@router.post("/payments/wire/{txn_id}/confirm")
async def wire_confirm(txn_id: str, payload: WireConfirmIn,
                       user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable.")
    if txn["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Accès refusé.")
    if txn.get("provider") != "wire":
        raise HTTPException(status_code=400, detail="Cette transaction n'est pas un virement.")
    if txn.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Déjà validé.")

    await db.payment_transactions.update_one(
        {"id": txn_id},
        {"$set": {
            "status": "wire_declared",
            "wire_user_reference": payload.reference,
            "wire_sender_name": payload.sender_name,
            "wire_sender_note": payload.sender_note,
            "wire_declared_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )

    return {"status": "declared", "txn_id": txn_id,
            "message": "Déclaration enregistrée. L'administrateur validera sous 24-72h."}
