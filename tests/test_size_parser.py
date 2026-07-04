from src.size_parser import SizeStatus, find_size_status


def test_finds_matching_size_case_insensitive():
    sizes = [SizeStatus("S", False), SizeStatus("M", True)]
    result = find_size_status(sizes, "s")
    assert result is not None
    assert result.label == "S"
    assert result.available is False


def test_ignores_extra_whitespace():
    sizes = [SizeStatus("  S  ", True)]
    result = find_size_status(sizes, "s")
    assert result is not None
    assert result.available is True


def test_returns_none_when_not_found():
    sizes = [SizeStatus("M", True)]
    assert find_size_status(sizes, "S") is None
