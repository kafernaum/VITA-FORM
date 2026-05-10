"""Service de paiement PayPal — flux `_xclick` (compte personnel/business standard).

L'utilisateur est redirigé vers une page PayPal hébergée. Il peut payer :
- avec son compte PayPal,
- ou par carte bancaire en mode invité (Guest Checkout, automatique).

À la confirmation, PayPal envoie un IPN (Instant Payment Notification) sur
notre webhook. On vérifie l'IPN en faisant un POST de retour à PayPal avec
`cmd=_notify-validate` ; si la réponse est `VERIFIED`, on déverrouille le livrable.

Aucune clé API n'est requise : seul l'email PayPal du marchand suffit.
"""
from __future__ import annotations

import os
import logging
from urllib.parse import urlencode

import requests

logger = logging.getLogger("vitaform.paypal")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _paypal_base() -> str:
    env = _env("PAYPAL_ENV", "live").lower()
    return "https://www.paypal.com" if env == "live" else "https://www.sandbox.paypal.com"


# Module-level constants (kept for compatibility; values read lazily below)
SUPPORTED_CURRENCIES = ["EUR", "USD", "GBP", "CAD", "CHF", "AUD", "JPY"]

PRICE_BY_CURRENCY = {
    "EUR": 14.90,
    "USD": 16.00,
    "GBP": 13.00,
    "CAD": 22.00,
    "CHF": 14.50,
    "AUD": 24.00,
    "JPY": 2400,
}


def get_business_email() -> str:
    return _env("PAYPAL_BUSINESS_EMAIL")


def get_merchant_id() -> str:
    return _env("PAYPAL_MERCHANT_ID")


def build_checkout_url(*, txn_id: str, item_name: str, amount: float,
                       currency: str, return_url: str, cancel_url: str,
                       notify_url: str, payer_email: str | None = None) -> str:
    """Construit l'URL PayPal `_xclick` (paiement unique).

    `custom` = txn_id : sera renvoyé dans l'IPN, sert d'identifiant interne.
    `no_shipping=1`   : pas d'adresse de livraison demandée.
    `rm=2`            : POST des paramètres au return_url (utile mais optionnel).
    """
    if not get_business_email():
        raise RuntimeError("PAYPAL_BUSINESS_EMAIL manquant dans l'environnement.")
    params = {
        "cmd": "_xclick",
        "business": get_business_email(),
        "item_name": item_name,
        "item_number": txn_id,
        "amount": f"{amount:.2f}" if currency != "JPY" else f"{int(amount)}",
        "currency_code": currency,
        "no_shipping": "1",
        "no_note": "1",
        "rm": "2",
        "return": return_url,
        "cancel_return": cancel_url,
        "notify_url": notify_url,
        "custom": txn_id,
        "charset": "utf-8",
    }
    mid = get_merchant_id()
    if mid:
        params["merchant_id"] = mid
    return f"{_paypal_base()}/cgi-bin/webscr?{urlencode(params)}"


def verify_ipn(raw_body: bytes) -> bool:
    """Vérifie un IPN reçu en réenvoyant la payload à PayPal.

    PayPal exige le préfixe `cmd=_notify-validate` suivi de la payload telle
    qu'elle a été reçue. Réponse attendue : `VERIFIED` ou `INVALID`.
    """
    payload = b"cmd=_notify-validate&" + raw_body
    try:
        resp = requests.post(
            f"{_paypal_base()}/cgi-bin/webscr", data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "VITA-FORM/1.0 (IPN-Verifier)"},
            timeout=20,
        )
        body = (resp.text or "").strip()
        if body == "VERIFIED":
            return True
        logger.warning("IPN PayPal NON vérifié, réponse=%r", body[:80])
        return False
    except Exception as exc:
        logger.exception("Échec vérification IPN: %s", exc)
        return False


def is_payment_acceptable(ipn: dict, expected_amount: float,
                           expected_currency: str) -> tuple[bool, str]:
    """Contrôles métier sur un IPN VÉRIFIÉ.

    1. payment_status doit être Completed
    2. receiver_email == PAYPAL_BUSINESS_EMAIL (anti-spoof)
    3. mc_currency == devise attendue
    4. mc_gross >= montant attendu (tolérance 0,01)
    """
    status = ipn.get("payment_status", "")
    if status != "Completed":
        return False, f"payment_status={status}"

    receiver = (ipn.get("receiver_email") or ipn.get("business") or "").lower()
    expected_email = get_business_email().lower()
    if receiver != expected_email:
        return False, f"receiver_email mismatch ({receiver})"

    if ipn.get("mc_currency") != expected_currency:
        return False, f"mc_currency mismatch ({ipn.get('mc_currency')})"

    try:
        gross = float(ipn.get("mc_gross", "0"))
    except (TypeError, ValueError):
        return False, "mc_gross invalide"
    if gross + 0.01 < expected_amount:
        return False, f"mc_gross {gross} < attendu {expected_amount}"

    return True, "ok"
