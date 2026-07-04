"""Carga de configuracion desde config.yaml y variables de entorno (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_ITEM_SELECTORS = [
    ".product-intro__size-radio .sku-item",
    ".product-intro__size .sku-item",
    "[class*='sku-list'] [class*='sku-item']",
    "[class*='size-radio'] [class*='item']",
]

DEFAULT_SOLDOUT_CLASSES = [
    "soldout",
    "sold-out",
    "disabled",
    "sku-item-disabled",
    "not-in-stock",
]

DEFAULT_SOLDOUT_CHILD_SELECTOR = "[class*='soldout'], [class*='sold-out']"


class ConfigError(Exception):
    pass


@dataclass
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    email_from: str
    email_to: str
    use_tls: bool = True


@dataclass
class Selectors:
    item_selectors: list[str] = field(default_factory=lambda: list(DEFAULT_ITEM_SELECTORS))
    soldout_classes: list[str] = field(default_factory=lambda: list(DEFAULT_SOLDOUT_CLASSES))
    soldout_child_selector: str = DEFAULT_SOLDOUT_CHILD_SELECTOR


@dataclass
class Product:
    name: str
    url: str
    sizes: list[str]


@dataclass
class AppConfig:
    check_interval_hours: float
    products: list[Product]
    smtp: SmtpConfig
    selectors: Selectors
    state_file: str = "state.json"
    navigation_timeout_ms: int = 45000
    headless: bool = True


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(
            f"Falta la variable de entorno obligatoria '{name}'. Revisa tu archivo .env "
            f"(usa .env.example como plantilla)."
        )
    return value


def load_smtp_config() -> SmtpConfig:
    return SmtpConfig(
        host=_require_env("SMTP_HOST"),
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=_require_env("SMTP_USER"),
        password=_require_env("SMTP_PASSWORD"),
        email_from=os.environ.get("EMAIL_FROM") or os.environ["SMTP_USER"],
        email_to=_require_env("EMAIL_TO"),
        use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() not in ("0", "false", "no"),
    )


def load_config(config_path: str | Path, env_path: str | Path | None = None) -> AppConfig:
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigError(
            f"No se encontro el archivo de configuracion '{config_path}'. "
            f"Copia config.example.yaml a config.yaml y editalo."
        )

    load_dotenv(dotenv_path=env_path) if env_path else load_dotenv()

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    products_raw = raw.get("products") or []
    if not products_raw:
        raise ConfigError("La configuracion no tiene ningun producto en 'products'.")

    products: list[Product] = []
    for idx, item in enumerate(products_raw):
        try:
            name = item["name"]
            url = item["url"]
            sizes = item["sizes"]
        except KeyError as exc:
            raise ConfigError(f"Producto #{idx} incompleto, falta la clave {exc}.") from exc
        if not isinstance(sizes, list) or not sizes:
            raise ConfigError(f"Producto '{name}' debe tener una lista 'sizes' no vacia.")
        products.append(Product(name=name, url=url, sizes=[str(s) for s in sizes]))

    selectors_raw = raw.get("selectors") or {}
    selectors = Selectors(
        item_selectors=selectors_raw.get("item_selectors", list(DEFAULT_ITEM_SELECTORS)),
        soldout_classes=selectors_raw.get("soldout_classes", list(DEFAULT_SOLDOUT_CLASSES)),
        soldout_child_selector=selectors_raw.get(
            "soldout_child_selector", DEFAULT_SOLDOUT_CHILD_SELECTOR
        ),
    )

    return AppConfig(
        check_interval_hours=float(raw.get("check_interval_hours", 3)),
        products=products,
        smtp=load_smtp_config(),
        selectors=selectors,
        state_file=raw.get("state_file", "state.json"),
        navigation_timeout_ms=int(raw.get("navigation_timeout_ms", 45000)),
        headless=bool(raw.get("headless", True)),
    )
