# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for marker replacement."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools.core.exceptions import MarkerError
from py_doc_tools.core.markers import replace_between_markers

if TYPE_CHECKING:
    from pathlib import Path


def test_replace_between_markers_preserves_indent(tmp_path: Path) -> None:
    """Replacement preserves marker indentation."""
    file_path = tmp_path / "mkdocs.yml"
    _ = file_path.write_text(
        """
nav:
  - API:
    # --- START ---
    - Old: old.md
    # --- END ---
""".lstrip(),
        encoding="utf-8",
    )

    replace_between_markers(
        file_path=file_path,
        start_marker="# --- START ---",
        end_marker="# --- END ---",
        new_block="- New: new.md",
    )

    content = file_path.read_text(encoding="utf-8")

    assert "    - New: new.md" in content
    assert "- Old: old.md" not in content


def test_replace_between_markers_raises_when_missing(tmp_path: Path) -> None:
    """Missing markers raise a dedicated marker error."""
    file_path = tmp_path / "mkdocs.yml"
    _ = file_path.write_text("nav: []\n", encoding="utf-8")

    with pytest.raises(MarkerError, match="Markers not found"):
        replace_between_markers(
            file_path=file_path,
            start_marker="# --- START ---",
            end_marker="# --- END ---",
            new_block="- New: new.md",
        )
