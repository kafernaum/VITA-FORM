"""VITA-FORM — Entrée FastAPI (assemble routers + middleware + lifecycle)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.bootstrap import bootstrap_app
from core.config import CORS_ORIGINS
from core.database import client
from routers import admin, auth, generations, meta, payments, rag, sources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("vitaform")

app = FastAPI(title="VITA-FORM API", version="1.0.0")
api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"app": "VITA-FORM", "status": "ok", "version": "1.0.0"}


# Mount feature routers under /api
api.include_router(auth.router)
api.include_router(meta.router)
api.include_router(generations.router)
api.include_router(sources.router)
api.include_router(rag.router)
api.include_router(payments.router)
api.include_router(admin.router)

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _on_startup():
    await bootstrap_app()


@app.on_event("shutdown")
async def _on_shutdown():
    client.close()
