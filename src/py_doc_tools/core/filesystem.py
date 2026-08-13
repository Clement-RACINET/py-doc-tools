"""Filesystem helpers."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def ensure_dir(path: Path) -> None:
    """Create a directory and its parents if needed."""
    path.mkdir(parents=True, exist_ok=True)


def remove_dir(path: Path) -> None:
    """Remove a directory tree if it exists."""
    if path.exists():
        shutil.rmtree(path)


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text and create parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8", newline="\n")


def read_text(path: Path) -> str:
    """Read UTF-8 text."""
    return path.read_text(encoding="utf-8")
