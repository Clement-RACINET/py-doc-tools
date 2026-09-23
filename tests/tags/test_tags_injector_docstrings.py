# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for safe source tag injection around docstrings."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from py_doc_tools.issues.model import DiagnosticIssue
from py_doc_tools.tags.injector import inject_issues_in_file

if TYPE_CHECKING:
    from pathlib import Path


def test_inject_issues_in_file_inserts_before_docstring(
    tmp_path: Path,
) -> None:
    """Ensure tags targeting docstrings are injected before the docstring."""
    source_path = tmp_path / "sample.py"
    _ = source_path.write_text(
        "\n".join(
            [
                "def __repr__() -> str:",
                '    """Return a representation.',
                "",
                "    Args:",
                "        None.",
                '    """',
                '    return "x"',
                "",
            ],
        ),
        encoding="utf-8",
    )

    issue = DiagnosticIssue(
        source="MkDocs",
        code="FALLBACK",
        severity="warning",
        category="MkDocs",
        message=(
            "griffe: magellan\\smm\\seeder\\uniform.py:4: "
            "Failed to get 'name: description' pair from 'None.'"
        ),
        file_path=source_path,
        line_number=4,
    )

    injected = inject_issues_in_file(
        file_path=source_path,
        issues=[issue],
        prefix="py-doc-tools",
        dry_run=False,
    )

    updated = source_path.read_text(encoding="utf-8")

    assert injected == 1
    assert "magellan/smm/seeder/uniform.py" in updated
    assert "\\smm\\" not in updated

    _ = ast.parse(updated)

    lines = updated.splitlines()
    assert lines[1].startswith("    # FIXME[py-doc-tools:MkDocs:FALLBACK]")
    assert lines[2].startswith('    """Return a representation.')
