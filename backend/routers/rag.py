"""VITA-FORM — Recherche jurisprudences (RAG) + lecture publique."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/jurisprudences", tags=["rag"])


@router.get("")
async def search_jurisprudences(
    q: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _: dict = Depends(get_current_user),
):
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
            del query["$text"]
            query["$or"] = [
                {"title": {"$regex": q, "$options": "i"}},
                {"body": {"$regex": q, "$options": "i"}},
            ]
            cursor = db.jurisprudences.find(query, projection).limit(limit)
    else:
        cursor = db.jurisprudences.find(query, projection).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(limit)
    return items


@router.get("/{jur_id}")
async def get_jurisprudence(jur_id: str, _: dict = Depends(get_current_user)):
    doc = await db.jurisprudences.find_one({"id": jur_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Jurisprudence introuvable.")
    return doc
