"""VITA-FORM — Upload/listing/suppression de sources documentaires."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.config import ALLOWED_UPLOAD_EXT, MAX_UPLOAD_BYTES
from core.database import db
from core.security import get_current_user
from sources_extractor import extract as extract_source
from storage_client import APP_NAME, put_object

logger = logging.getLogger("vitaform")

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/upload")
async def upload_source(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    name = file.filename or "source.bin"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
    if ext not in ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez PDF, DOCX ou TXT.",
        )
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


@router.get("")
async def list_sources(user: dict = Depends(get_current_user)):
    rows = await db.sources.find(
        {"user_id": user["id"], "is_deleted": False},
        {"_id": 0, "extracted_text": 0, "storage_path": 0},
    ).sort("created_at", -1).to_list(200)
    return rows


@router.delete("/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(get_current_user)):
    res = await db.sources.update_one(
        {"id": source_id, "user_id": user["id"]},
        {"$set": {"is_deleted": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source introuvable.")
    return {"status": "ok"}
