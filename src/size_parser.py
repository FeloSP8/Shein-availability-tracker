"""Logica pura (sin red ni navegador) para interpretar las tallas leidas de la pagina."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class SizeStatus:
    label: str
    available: bool


def _normalize(label: str) -> str:
    return " ".join(label.strip().upper().split())


def find_size_status(sizes: Iterable[SizeStatus], target_label: str) -> Optional[SizeStatus]:
    """Busca la talla objetivo (comparacion insensible a mayusculas/espacios)."""
    target = _normalize(target_label)
    for size in sizes:
        if _normalize(size.label) == target:
            return size
    return None
