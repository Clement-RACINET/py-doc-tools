"""Title formatting helpers."""

from __future__ import annotations


def human_title(name: str) -> str:
    """Convert a snake/kebab-case name into a human-readable title."""
    return name.replace("_", " ").replace("-", " ").strip().title()
