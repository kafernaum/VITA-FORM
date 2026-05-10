"""Service email transactionnel Resend (envoi non-bloquant)."""
import os
import asyncio
import logging

import resend

logger = logging.getLogger("vitaform.email")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _payment_html(full_name: str, topic: str, generation_id: str) -> str:
    link = f"{PUBLIC_APP_URL}/preview/{generation_id}" if PUBLIC_APP_URL else "#"
    return f"""
<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#0A1128;font-family:Georgia,serif;padding:40px 0;">
  <tr><td align="center">
    <table cellpadding="0" cellspacing="0" border="0" width="600" style="background:#131B33;border:1px solid #D4AF37;color:#F8FAFC;">
      <tr><td style="padding:40px 50px;">
        <p style="font-size:11px;letter-spacing:0.3em;color:#D4AF37;margin:0 0 24px;">VITA-FORM · DOCTRINA VITALIS</p>
        <h1 style="font-size:28px;color:#F8FAFC;margin:0 0 18px;font-weight:normal;">Paiement confirmé</h1>
        <p style="font-size:16px;line-height:1.6;color:#E2E8F0;margin:0 0 18px;">Bonjour {full_name},</p>
        <p style="font-size:16px;line-height:1.6;color:#E2E8F0;margin:0 0 18px;">
          Nous confirmons la réception de votre paiement pour le livrable suivant :
        </p>
        <p style="font-size:18px;line-height:1.4;color:#F3E5AB;font-style:italic;margin:0 0 28px;border-left:3px solid #D4AF37;padding:8px 16px;">
          {topic}
        </p>
        <p style="font-size:16px;line-height:1.6;color:#E2E8F0;margin:0 0 28px;">
          Votre livrable est désormais accessible en téléchargement (PDF, Word, Slides) depuis votre bibliothèque VITA-FORM.
        </p>
        <p style="margin:0 0 32px;">
          <a href="{link}" style="background:#D4AF37;color:#0A1128;text-decoration:none;padding:14px 28px;font-weight:bold;display:inline-block;letter-spacing:0.05em;">
            Accéder au livrable
          </a>
        </p>
        <p style="font-size:14px;line-height:1.6;color:#94A3B8;margin:0 0 8px;font-style:italic;">
          « On ne manipule pas des chiffres, mais des âmes. »
        </p>
        <p style="font-size:12px;color:#64748B;margin:32px 0 0;">— Théorie Vitaliste des Finances Publiques · Pr. Ahmed ELY Mustapha</p>
      </td></tr>
    </table>
  </td></tr>
</table>
"""


async def send_payment_confirmation(recipient_email: str, full_name: str,
                                     topic: str, generation_id: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY missing; skipping email")
        return False
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": "Votre livrable VITA-FORM est débloqué",
        "html": _payment_html(full_name, topic, generation_id),
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info("Resend email sent to %s id=%s", recipient_email, result.get("id"))
        return True
    except Exception as exc:
        logger.exception("Resend send failed: %s", exc)
        return False
