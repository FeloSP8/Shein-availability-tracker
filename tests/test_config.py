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
GMAIL_USER=user@gmail.com
GMAIL_APP_PASSWORD=secret
EMAIL_TO=notify@example.com
"""

ENV_KEYS = ["GMAIL_USER", "GMAIL_APP_PASSWORD", "EMAIL_TO"]


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_config_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    config_path = _write(tmp_path, "config.yaml", VALID_CONFIG)
    env_path = _write(tmp_path, ".env", VALID_ENV)

    config = load_config(config_path, env_path)

    assert config.check_interval_hours == 2
    assert len(config.products) == 1
    assert config.products[0].sizes == ["S"]
    assert config.smtp.host == "smtp.gmail.com"
    assert config.smtp.port == 587
    assert config.smtp.user == "user@gmail.com"
    assert config.smtp.email_from == "user@gmail.com"
    assert config.smtp.email_to == "notify@example.com"


def test_missing_config_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yaml")


def test_missing_products_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    config_path = _write(tmp_path, "config.yaml", "check_interval_hours: 2\nproducts: []\n")
    env_path = _write(tmp_path, ".env", VALID_ENV)
    with pytest.raises(ConfigError):
        load_config(config_path, env_path)


def test_missing_gmail_env_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    config_path = _write(tmp_path, "config.yaml", VALID_CONFIG)
    env_path = _write(tmp_path, ".env", "GMAIL_USER=user@gmail.com\n")
    with pytest.raises(ConfigError):
        load_config(config_path, env_path)
