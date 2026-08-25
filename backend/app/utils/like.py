"""Helpers for building SQL ``LIKE``/``ILIKE`` patterns safely."""

from __future__ import annotations


def escape_like(value: str) -> str:
    """Escape SQL ``LIKE`` wildcards so user input matches literally.

    The order matters: backslashes must be escaped first, otherwise the
    escapes added for ``%`` and ``_`` could themselves be interpreted as
    escaping the following character.
    """
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
