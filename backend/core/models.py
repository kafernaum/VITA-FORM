"""VITA-FORM — Pydantic models partagés."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    user: dict


class GenerationCreate(BaseModel):
    topic: str = Field(min_length=4)
    institution_id: str
    cycle: str
    duration: str
    year: int = Field(default_factory=lambda: datetime.now().year)
    sources: Optional[str] = ""
    source_ids: Optional[List[str]] = None
    jurisprudence_ids: Optional[List[str]] = None
    language: Literal["fr", "ar"] = "fr"


class VitalistAnalyzeIn(BaseModel):
    document_type: Literal[
        "Budget", "Convention de prêt", "Bilan", "Loi de finances",
        "Marché public", "Dette publique", "Autre"
    ]
    document_text: str = Field(min_length=20)
    monetary_amount: float = Field(gt=0)
    country_code: str = Field(default="FR")
    daily_salary: Optional[float] = None
    title: str = Field(default="Analyse vitaliste")
    language: Literal["fr", "ar"] = "fr"


class InstitutionIn(BaseModel):
    name: str
    country: str
    country_code: str
    city: str
    type: str


class JurisprudenceIn(BaseModel):
    title: str = Field(min_length=3)
    country: str
    body: str = Field(min_length=20)
    reference: Optional[str] = ""
    tags: Optional[List[str]] = None


class BankAccountIn(BaseModel):
    holder_name: str = Field(min_length=2)
    bank_name: str = Field(min_length=2)
    iban: str = Field(min_length=10)
    bic: Optional[str] = ""
    currency: str = "EUR"
    country: str = "France"
    instructions: Optional[str] = ""
    is_active: bool = True


class WireInitiateIn(BaseModel):
    generation_id: str
    bank_account_id: str
    currency: str = "EUR"


class WireConfirmIn(BaseModel):
    reference: str = Field(min_length=2)
    sender_name: str = Field(min_length=2)
    sender_note: Optional[str] = ""


class PayPalCheckoutIn(BaseModel):
    generation_id: str
    origin_url: str
    currency: str = "EUR"
