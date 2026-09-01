from app.utils.like import escape_like


def test_escape_like_percent() -> None:
    assert escape_like("100%") == "100\\%"


def test_escape_like_underscore() -> None:
    assert escape_like("a_b") == "a\\_b"


def test_escape_like_backslash_first() -> None:
    assert escape_like(r"a\b") == r"a\\b"


def test_escape_like_combined() -> None:
    assert escape_like(r"100%_\\") == r"100\%\_\\\\"


def test_escape_like_plain_string_is_unchanged() -> None:
    assert escape_like("plain search") == "plain search"
