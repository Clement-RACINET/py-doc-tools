# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for generated diagnostic tag rendering."""

from __future__ import annotations

from pathlib import Path

from py_doc_tools.issues.model import DiagnosticIssue
from py_doc_tools.tags.generated import render_generated_tag


def test_render_generated_tag_normalizes_windows_paths() -> None:
    """Ensure generated tags do not contain raw Windows backslashes."""
    issue = DiagnosticIssue(
        source="MkDocs",
        code="FALLBACK",
        severity="warning",
        category="MkDocs",
        message=(
            "griffe: magellan\\smm\\seeder\\uniform.py:131: "
            "Failed to get 'name: description' pair from 'None.'"
        ),
        file_path=Path("magellan/smm/seeder/uniform.py"),
        line_number=131,
    )

    tag = render_generated_tag(issue)

    assert "magellan/smm/seeder/uniform.py" in tag
    assert "\\smm\\" not in tag
    assert "\\u" not in tag
