"""Persistencia simple en JSON para no repetir avisos por correo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def state_key(product_url: str, size: str) -> str:
    return f"{product_url}::{size.strip().upper()}"


def load_state(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(path: str | Path, state: dict[str, Any]) -> None:
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False, sort_keys=True)
    tmp_path.replace(path)
