from pathlib import Path

from src.state import load_state, save_state, state_key


def test_load_state_missing_file_returns_empty(tmp_path: Path):
    assert load_state(tmp_path / "does_not_exist.json") == {}


def test_save_and_load_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    data = {"a::S": {"available": True, "notified": True}}
    save_state(path, data)
    assert load_state(path) == data


def test_load_state_corrupt_file_returns_empty(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text("not json", encoding="utf-8")
    assert load_state(path) == {}


def test_state_key_normalizes_size():
    assert state_key("https://x", "s") == state_key("https://x", "S")
