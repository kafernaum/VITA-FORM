"""VITA-FORM — Routes auth (register, login, me)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core.database import db
from core.models import LoginIn, RegisterIn, TokenOut
from core.security import (
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
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


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants invalides.")
    token = create_token(user["id"], user.get("role", "user"))
    return TokenOut(access_token=token, user={
        "id": user["id"], "email": user["email"], "full_name": user["full_name"],
        "role": user.get("role", "user"), "vip": user.get("vip", False),
    })


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
