"""Orquesta una pasada de comprobacion sobre todos los productos configurados."""
from __future__ import annotations

import logging

from .browser_client import BrowserFetchError, fetch_size_statuses
from .config import AppConfig, Product
from .notifier import send_availability_email
from .size_parser import find_size_status
from .state import load_state, save_state, state_key

logger = logging.getLogger(__name__)


def check_product(config: AppConfig, product: Product, state: dict) -> None:
    try:
        statuses = fetch_size_statuses(
            product.url,
            config.selectors,
            headless=config.headless,
            navigation_timeout_ms=config.navigation_timeout_ms,
        )
    except BrowserFetchError as exc:
        logger.error("Error comprobando '%s': %s", product.name, exc)
        return

    for size_label in product.sizes:
        status = find_size_status(statuses, size_label)
        key = state_key(product.url, size_label)

        if status is None:
            logger.warning(
                "Talla '%s' no encontrada para '%s'. Tallas leidas: %s",
                size_label,
                product.name,
                [s.label for s in statuses],
            )
            continue

        previously_notified = bool(state.get(key, {}).get("notified"))

        if status.available and not previously_notified:
            try:
                send_availability_email(config.smtp, product.name, size_label, product.url)
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo enviar el correo para '%s' talla %s", product.name, size_label)
                continue
            state[key] = {"available": True, "notified": True}
            logger.info("'%s' talla %s: ahora disponible, aviso enviado.", product.name, size_label)
        elif not status.available:
            if previously_notified:
                logger.info("'%s' talla %s: vuelve a estar agotada.", product.name, size_label)
            state[key] = {"available": False, "notified": False}
        else:
            logger.debug("'%s' talla %s: disponible, ya se aviso antes.", product.name, size_label)


def run_check_once(config: AppConfig) -> None:
    state = load_state(config.state_file)
    for product in config.products:
        check_product(config, product, state)
    save_state(config.state_file, state)
