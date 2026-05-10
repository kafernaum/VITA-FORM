"""VITA-FORM — Logique de démarrage (seeds, index, admin)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from jurisprudence_seed import JURISPRUDENCES_SEED
from seeds import INSTITUTIONS_SEED
from storage_client import init_storage

from .config import ADMIN_EMAIL, ADMIN_PASSWORD
from .database import db
from .security import hash_password

logger = logging.getLogger("vitaform")


async def bootstrap_app() -> None:
    """Initialise le stockage, seede institutions/jurisprudences + admin."""
    try:
        init_storage()
    except Exception as exc:  # pragma: no cover
        logger.warning("Storage init failed: %s", exc)

    if await db.institutions.count_documents({}) == 0:
        for it in INSTITUTIONS_SEED:
            await db.institutions.insert_one({**it, "id": str(uuid.uuid4())})
        logger.info("Seeded %d institutions", len(INSTITUTIONS_SEED))

    try:
        await db.jurisprudences.create_index(
            [("title", "text"), ("body", "text"), ("reference", "text")],
            default_language="french",
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Jurisprudence text index: %s", exc)

    if await db.jurisprudences.count_documents({}) == 0:
        for j in JURISPRUDENCES_SEED:
            await db.jurisprudences.insert_one({
                "id": str(uuid.uuid4()),
                **j,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.info("Seeded %d jurisprudences", len(JURISPRUDENCES_SEED))

    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": ADMIN_EMAIL,
            "full_name": "Administrateur VITA-FORM",
            "password_hash": hash_password(ADMIN_PASSWORD),
            "role": "admin",
            "vip": True,
            "vip_until": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Seeded admin %s", ADMIN_EMAIL)
