"""VITA-FORM — configuration globale (env vars + constantes)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Mongo
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# Auth
JWT_SECRET = os.environ.get("JWT_SECRET", "vitaform-secret")
JWT_ALG = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXP_HOURS = 24 * 7

# LLM
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
LLM_MODEL = ("anthropic", "claude-sonnet-4-5-20250929")

# Paywall
PAYWALL_PRICE = float(os.environ.get("PAYWALL_PRICE_EUR", "14.90"))

# Admin seed
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@vita-form.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "VitaForm2026!Admin")

# CORS
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# Public app URL (pour PayPal IPN notify_url)
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "")

# Uploads
ALLOWED_UPLOAD_EXT = {"pdf", "docx", "txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
