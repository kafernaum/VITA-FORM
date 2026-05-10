"""VITA-FORM — Routes admin (users, stats, institutions, jurisprudences,
bank accounts, validation des virements, recettes)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core.database import db
from core.helpers import send_payment_email
from core.models import BankAccountIn, InstitutionIn, JurisprudenceIn
from core.security import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@router.get("/users")
async def admin_users():
    items = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for it in items:
        it["generations_count"] = await db.generations.count_documents({"user_id": it["id"]})
        it["payments_count"] = await db.payment_transactions.count_documents(
            {"user_id": it["id"], "payment_status": "paid"})
    return items


@router.post("/users/{user_id}/vip")
async def admin_set_vip(user_id: str, vip: bool = True, days: Optional[int] = None):
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


# ---------------------------------------------------------------------------
# Stats & generations
# ---------------------------------------------------------------------------
@router.get("/stats")
async def admin_stats():
    return {
        "users": await db.users.count_documents({}),
        "generations": await db.generations.count_documents({}),
        "payments": await db.payment_transactions.count_documents({"payment_status": "paid"}),
        "institutions": await db.institutions.count_documents({}),
    }


@router.get("/generations")
async def admin_generations():
    items = await db.generations.find(
        {}, {"_id": 0, "content": 0}
    ).sort("created_at", -1).to_list(500)
    return items


# ---------------------------------------------------------------------------
# Institutions
# ---------------------------------------------------------------------------
@router.post("/institutions")
async def admin_create_institution(payload: InstitutionIn):
    doc = {**payload.model_dump(), "id": str(uuid.uuid4())}
    await db.institutions.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.delete("/institutions/{inst_id}")
async def admin_delete_institution(inst_id: str):
    res = await db.institutions.delete_one({"id": inst_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Institution introuvable.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Jurisprudences
# ---------------------------------------------------------------------------
@router.post("/jurisprudences")
async def admin_create_jurisprudence(payload: JurisprudenceIn):
    doc = {
        "id": str(uuid.uuid4()),
        **payload.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.jurisprudences.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.delete("/jurisprudences/{jur_id}")
async def admin_delete_jurisprudence(jur_id: str):
    res = await db.jurisprudences.delete_one({"id": jur_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Jurisprudence introuvable.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Bank accounts
# ---------------------------------------------------------------------------
@router.post("/bank-accounts")
async def admin_create_bank_account(payload: BankAccountIn):
    doc = {
        "id": str(uuid.uuid4()),
        **payload.model_dump(),
        "iban": payload.iban.replace(" ", "").upper(),
        "bic": (payload.bic or "").replace(" ", "").upper(),
        "currency": payload.currency.upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bank_accounts.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/bank-accounts")
async def admin_list_bank_accounts():
    items = await db.bank_accounts.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return items


@router.patch("/bank-accounts/{acct_id}")
async def admin_update_bank_account(acct_id: str, payload: BankAccountIn):
    update = {
        **payload.model_dump(),
        "iban": payload.iban.replace(" ", "").upper(),
        "bic": (payload.bic or "").replace(" ", "").upper(),
        "currency": payload.currency.upper(),
    }
    res = await db.bank_accounts.update_one({"id": acct_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Compte introuvable.")
    doc = await db.bank_accounts.find_one({"id": acct_id}, {"_id": 0})
    return doc


@router.delete("/bank-accounts/{acct_id}")
async def admin_delete_bank_account(acct_id: str):
    res = await db.bank_accounts.delete_one({"id": acct_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Compte introuvable.")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Wire payments — validation
# ---------------------------------------------------------------------------
@router.get("/payments/pending")
async def admin_pending_payments():
    rows = await db.payment_transactions.find(
        {"provider": "wire", "payment_status": "pending"}, {"_id": 0},
    ).sort("created_at", -1).to_list(200)
    for r in rows:
        gen = await db.generations.find_one({"id": r["generation_id"]},
                                            {"_id": 0, "topic": 1})
        r["generation_topic"] = (gen or {}).get("topic", "—")
    return rows


@router.post("/payments/{txn_id}/validate")
async def admin_validate_wire(txn_id: str):
    txn = await db.payment_transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction introuvable.")
    if txn.get("payment_status") == "paid":
        return {"status": "already_paid"}
    await db.payment_transactions.update_one(
        {"id": txn_id},
        {"$set": {
            "payment_status": "paid",
            "status": "complete",
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    await db.generations.update_one(
        {"id": txn["generation_id"]},
        {"$set": {
            "paid": True,
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "payment_txn_id": txn_id,
        }},
    )
    await send_payment_email(txn["generation_id"], txn.get("user_email"))
    return {"status": "validated"}


@router.post("/payments/{txn_id}/reject")
async def admin_reject_wire(txn_id: str, reason: str = ""):
    res = await db.payment_transactions.update_one(
        {"id": txn_id},
        {"$set": {
            "status": "rejected",
            "rejection_reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction introuvable.")
    return {"status": "rejected"}


# ---------------------------------------------------------------------------
# Recettes
# ---------------------------------------------------------------------------
@router.get("/revenue")
async def admin_revenue():
    pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {
            "_id": {
                "month": {"$substr": ["$updated_at", 0, 7]},
                "currency": "$currency",
                "method": {"$ifNull": ["$method", "$provider"]},
            },
            "count": {"$sum": 1},
            "total": {"$sum": "$amount"},
        }},
        {"$sort": {"_id.month": -1}},
    ]
    rows = await db.payment_transactions.aggregate(pipeline).to_list(500)

    by_currency: dict = {}
    by_month: dict = {}
    for r in rows:
        cur = r["_id"]["currency"]
        mo = r["_id"]["month"]
        by_currency.setdefault(cur, {"count": 0, "total": 0.0})
        by_currency[cur]["count"] += r["count"]
        by_currency[cur]["total"] += r["total"]
        by_month.setdefault(mo, [])
        by_month[mo].append({
            "currency": cur,
            "method": r["_id"].get("method", "?"),
            "count": r["count"],
            "total": round(r["total"], 2),
        })

    return {
        "by_currency": {c: {"count": v["count"], "total": round(v["total"], 2)}
                        for c, v in by_currency.items()},
        "by_month": [{"month": m, "rows": rows_}
                     for m, rows_ in sorted(by_month.items(), reverse=True)],
        "transactions_total": await db.payment_transactions.count_documents(
            {"payment_status": "paid"}),
    }
