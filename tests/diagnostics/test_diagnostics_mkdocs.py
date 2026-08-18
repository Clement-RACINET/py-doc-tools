"""Tests for MkDocs diagnostics parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.diagnostics.mkdocs import parse_mkdocs_output

if TYPE_CHECKING:
    from pathlib import Path

MULTILINE_WARNING_LINE = 12


def test_parse_mkdocs_output_extracts_typing_issue(tmp_path: Path) -> None:
    """MkDocs parser extracts typing-related diagnostics."""
    source_file = tmp_path / "src" / "demo.py"
    source_file.parent.mkdir()
    _ = source_file.write_text("def demo(value):\n    return value\n", encoding="utf-8")

    output = "WARNING -  src/demo.py:1: Missing type annotation for parameter `value`\n"

    issues = parse_mkdocs_output(output, project_root=tmp_path)

    assert len(issues) == 1
    assert issues[0].source == "MkDocs"
    assert issues[0].code == "TYPING"
    assert issues[0].severity == "todo"
    assert issues[0].file_path == source_file
    assert issues[0].line_number == 1


def test_parse_mkdocs_output_extracts_docformat_issue(tmp_path: Path) -> None:
    """MkDocs parser extracts docstring/signature diagnostics."""
    source_file = tmp_path / "src" / "demo.py"
    source_file.parent.mkdir()
    _ = source_file.write_text("def demo() -> None:\n    pass\n", encoding="utf-8")

    output = (
        "WARNING -  src/demo.py:1: Parameter `missing` documented "
        "but not present in signature\n"
    )

    issues = parse_mkdocs_output(output, project_root=tmp_path)

    assert len(issues) == 1
    assert issues[0].code == "DOCFORMAT"
    assert issues[0].severity == "fixme"
    assert issues[0].file_path == source_file
    assert issues[0].line_number == 1


def test_parse_mkdocs_output_extracts_fallback_issue(tmp_path: Path) -> None:
    """MkDocs parser keeps unclassified diagnostics as fallback issues."""
    output = "WARNING -  Some global navigation warning\n"

    issues = parse_mkdocs_output(output, project_root=tmp_path)

    assert len(issues) == 1
    assert issues[0].code == "FALLBACK"
    assert issues[0].severity == "warning"
    assert issues[0].file_path is None
    assert issues[0].line_number is None


def test_parse_mkdocs_output_groups_multiline_warning(tmp_path: Path) -> None:
    """MkDocs parser groups continuation lines with their warning."""
    output = "\n".join(
        [
            "WARNING -  src/demo.py:12: Parameter documented incorrectly",
            "  Details: expected `value` in signature",
            "",
        ],
    )

    issues = parse_mkdocs_output(output, project_root=tmp_path)

    assert len(issues) == 1
    assert issues[0].code == "DOCFORMAT"
    assert issues[0].line_number == MULTILINE_WARNING_LINE


def test_parse_mkdocs_output_ignores_normal_output(tmp_path: Path) -> None:
    """MkDocs parser ignores non-warning output."""
    output = "INFO - Cleaning site directory\nINFO - Documentation built\n"

    assert parse_mkdocs_output(output, project_root=tmp_path) == []
