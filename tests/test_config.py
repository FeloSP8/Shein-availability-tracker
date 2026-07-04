from pathlib import Path

import pytest

from src.config import ConfigError, load_config

VALID_CONFIG = """
check_interval_hours: 2
products:
  - name: "Vestido"
    url: "https://es.shein.com/vestido-p-123.html"
    sizes: ["S"]
"""

VALID_ENV = """
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=secret
EMAIL_TO=user@example.com
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_config_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]:
        monkeypatch.delenv(key, raising=False)
    config_path = _write(tmp_path, "config.yaml", VALID_CONFIG)
    env_path = _write(tmp_path, ".env", VALID_ENV)

    config = load_config(config_path, env_path)

    assert config.check_interval_hours == 2
    assert len(config.products) == 1
    assert config.products[0].sizes == ["S"]
    assert config.smtp.host == "smtp.gmail.com"
    assert config.smtp.email_from == "user@example.com"


def test_missing_config_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yaml")


def test_missing_products_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]:
        monkeypatch.delenv(key, raising=False)
    config_path = _write(tmp_path, "config.yaml", "check_interval_hours: 2\nproducts: []\n")
    env_path = _write(tmp_path, ".env", VALID_ENV)
    with pytest.raises(ConfigError):
        load_config(config_path, env_path)


def test_missing_smtp_env_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]:
        monkeypatch.delenv(key, raising=False)
    config_path = _write(tmp_path, "config.yaml", VALID_CONFIG)
    env_path = _write(tmp_path, ".env", "SMTP_HOST=smtp.gmail.com\n")
    with pytest.raises(ConfigError):
        load_config(config_path, env_path)
