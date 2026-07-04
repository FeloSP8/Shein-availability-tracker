"""Envio de notificaciones por correo (SMTP)."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from .config import SmtpConfig

logger = logging.getLogger(__name__)


def send_availability_email(smtp_cfg: SmtpConfig, product_name: str, size: str, url: str) -> None:
    subject = f"Disponible: {product_name} (talla {size})"
    body = (
        f"La talla {size} de '{product_name}' ya esta disponible en SheIn.\n\n"
        f"Enlace: {url}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_cfg.email_from
    msg["To"] = smtp_cfg.email_to
    msg.set_content(body)

    with smtplib.SMTP(smtp_cfg.host, smtp_cfg.port, timeout=20) as server:
        if smtp_cfg.use_tls:
            server.starttls()
        server.login(smtp_cfg.user, smtp_cfg.password)
        server.send_message(msg)

    logger.info("Correo enviado a %s sobre '%s' talla %s", smtp_cfg.email_to, product_name, size)
