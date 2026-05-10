"""VITA-FORM — Métadonnées (cycles, durations, salaires) + institutions publiques."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from core.database import db
from seeds import CYCLES, DAILY_SALARIES, DURATIONS

router = APIRouter(tags=["meta"])


@router.get("/meta/options")
async def meta_options():
    return {"cycles": CYCLES, "durations": DURATIONS, "daily_salaries": DAILY_SALARIES}


@router.get("/institutions")
async def list_institutions(country_code: Optional[str] = None):
    query = {}
    if country_code:
        query["country_code"] = country_code.upper()
    items = await db.institutions.find(query, {"_id": 0}).sort("country", 1).to_list(500)
    return items
