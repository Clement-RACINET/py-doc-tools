# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for filesystem helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.core.filesystem import ensure_dir, read_text, remove_dir, write_text

if TYPE_CHECKING:
    from pathlib import Path


def test_filesystem_helpers(tmp_path: Path) -> None:
    """Filesystem helpers create, write, read and remove paths."""
    folder = tmp_path / "nested" / "folder"
    ensure_dir(folder)

    assert folder.exists()

    file_path = folder / "file.txt"
    write_text(file_path, "hello")

    assert read_text(file_path) == "hello"

    remove_dir(tmp_path / "nested")

    assert not (tmp_path / "nested").exists()


def test_remove_dir_ignores_missing_path(tmp_path: Path) -> None:
    """Removing a missing directory is a no-op."""
    remove_dir(tmp_path / "missing")
