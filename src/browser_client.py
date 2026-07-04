"""Cliente basado en Playwright para leer el estado real (renderizado) de una
pagina de producto de SheIn.

SheIn no publica una API oficial de stock por talla, y su API interna
cambia de forma y de firma con frecuencia. Por eso este cliente abre la
pagina en un navegador real (Chromium headless) y lee lo mismo que veria una
persona: si el boton/etiqueta de la talla aparece marcado como agotado.

Esto es mas resistente a cambios que llamar a un endpoint no documentado,
pero depende de los selectores CSS definidos en `config.yaml -> selectors`.
Si SheIn cambia su HTML, usa `python main.py debug --url <url>` para volcar
una captura y el HTML de la pagina y poder ajustar los selectores.
"""
from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

from .config import Selectors
from .size_parser import SizeStatus

logger = logging.getLogger(__name__)

DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Textos habituales de interstitiales "abrir en la app" que a veces se
# muestran antes de dejar ver la pagina de producto en el navegador.
CONTINUE_IN_BROWSER_TEXTS = [
    "Continuar en el navegador",
    "Seguir en el navegador",
    "Continue in browser",
    "Continue on web",
    "No, gracias",
    "Ahora no",
]


class BrowserFetchError(Exception):
    pass


def _new_browser(playwright, headless: bool) -> Browser:
    return playwright.chromium.launch(headless=headless)


def _dismiss_app_interstitial(page) -> None:
    for text in CONTINUE_IN_BROWSER_TEXTS:
        try:
            locator = page.get_by_text(text, exact=False)
            if locator.count() > 0:
                locator.first.click(timeout=2000)
                page.wait_for_timeout(500)
        except Exception:  # noqa: BLE001 - el interstitial es best-effort
            continue


def _extract_size_statuses(page, selectors: Selectors) -> list[SizeStatus]:
    for item_selector in selectors.item_selectors:
        elements = page.query_selector_all(item_selector)
        if not elements:
            continue

        statuses: list[SizeStatus] = []
        for element in elements:
            raw_text = element.inner_text() or ""
            lines = raw_text.strip().splitlines()
            label = lines[0].strip() if lines else ""
            if not label:
                continue

            class_name = (element.get_attribute("class") or "").lower()
            aria_disabled = (element.get_attribute("aria-disabled") or "").lower() == "true"
            has_soldout_class = any(cls in class_name for cls in selectors.soldout_classes)
            has_soldout_child = False
            if selectors.soldout_child_selector:
                has_soldout_child = element.query_selector(selectors.soldout_child_selector) is not None

            is_soldout = aria_disabled or has_soldout_class or has_soldout_child
            statuses.append(SizeStatus(label=label, available=not is_soldout))

        if statuses:
            return statuses

    return []


def fetch_size_statuses(
    url: str,
    selectors: Selectors,
    *,
    headless: bool = True,
    navigation_timeout_ms: int = 45000,
) -> list[SizeStatus]:
    """Abre `url` en un navegador headless y devuelve el estado de cada talla."""
    with sync_playwright() as playwright:
        browser = _new_browser(playwright, headless)
        try:
            context = browser.new_context(
                user_agent=DESKTOP_USER_AGENT,
                locale="es-ES",
                extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
            )
            page = context.new_page()
            page.set_default_navigation_timeout(navigation_timeout_ms)
            page.set_default_timeout(navigation_timeout_ms)

            try:
                page.goto(url, wait_until="domcontentloaded")
            except Exception as exc:  # noqa: BLE001
                raise BrowserFetchError(f"No se pudo abrir la URL '{url}': {exc}") from exc

            try:
                page.wait_for_load_state("networkidle", timeout=navigation_timeout_ms)
            except Exception:  # noqa: BLE001 - algunas paginas nunca llegan a 'idle'
                pass

            _dismiss_app_interstitial(page)

            if "shein.com" not in page.url:
                raise BrowserFetchError(
                    f"La navegacion no llego a una pagina de shein.com (URL final: {page.url}). "
                    f"El enlace para compartir puede haber expirado; prueba a usar la URL "
                    f"directa del producto (https://.../-p-<id>.html) en config.yaml."
                )

            statuses = _extract_size_statuses(page, selectors)
            if not statuses:
                raise BrowserFetchError(
                    "No se encontro ningun selector de talla en la pagina. Ajusta "
                    "'selectors.item_selectors' en config.yaml (usa 'python main.py debug' "
                    "para inspeccionar el HTML)."
                )
            return statuses
        finally:
            browser.close()


def dump_debug_snapshot(
    url: str,
    output_dir: str | Path,
    *,
    headless: bool = True,
    navigation_timeout_ms: int = 45000,
) -> tuple[Path, Path, str]:
    """Guarda una captura de pantalla y el HTML final para calibrar selectores."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = output_dir / "snapshot.png"
    html_path = output_dir / "snapshot.html"

    with sync_playwright() as playwright:
        browser = _new_browser(playwright, headless)
        try:
            context = browser.new_context(
                user_agent=DESKTOP_USER_AGENT,
                locale="es-ES",
                extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
            )
            page = context.new_page()
            page.set_default_navigation_timeout(navigation_timeout_ms)
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=navigation_timeout_ms)
            except Exception:  # noqa: BLE001
                pass
            _dismiss_app_interstitial(page)
            page.screenshot(path=str(screenshot_path), full_page=True)
            html_path.write_text(page.content(), encoding="utf-8")
            final_url = page.url
        finally:
            browser.close()

    return screenshot_path, html_path, final_url
