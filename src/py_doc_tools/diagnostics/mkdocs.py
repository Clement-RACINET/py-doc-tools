# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""MkDocs diagnostics collection and parsing."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.subprocesses import run_command
from py_doc_tools.issues.model import DiagnosticIssue, IssueSeverity

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig

MKDOCS_WARNING_PATTERN = re.compile(
    r"^(?P<level>WARNING|ERROR)\s+-\s+(?P<message>.*)$",
    re.IGNORECASE,
)

PYTHON_PATH_PATTERN = re.compile(
    r"(?P<path>[A-Za-z0-9_./\\-]+\.py)(?::(?P<line>\d+))?",
)


@dataclass(frozen=True, slots=True)
class MkDocsCollectionResult:
    """Result of a MkDocs diagnostic collection run."""

    issues: list[DiagnosticIssue]
    return_code: int
    raw_output: str
    command: list[str]


def build_mkdocs_command(cfg: DocToolsConfig) -> list[str]:
    """Build the MkDocs diagnostics command."""
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    command = [
        sys.executable,
        "-m",
        "mkdocs",
        "build",
        "-f",
        str(cfg.mkdocs_config),
    ]

    if cfg.diagnostics.mkdocs_strict:
        command.append("--strict")

    return command


def collect_mkdocs_issues(cfg: DocToolsConfig) -> MkDocsCollectionResult:
    """Run MkDocs and return normalized diagnostic issues."""
    command = build_mkdocs_command(cfg)
    proc = run_command(
        command,
        cwd=cfg.project_root,
        check=False,
        capture_output=True,
    )

    raw_output = _combined_output(proc.stdout, proc.stderr)
    issues = parse_mkdocs_output(raw_output, project_root=cfg.project_root)

    return MkDocsCollectionResult(
        issues=issues,
        return_code=proc.returncode,
        raw_output=raw_output,
        command=command,
    )


def parse_mkdocs_output(
    output: str,
    *,
    project_root: Path,
) -> list[DiagnosticIssue]:
    """Parse MkDocs output into normalized diagnostic issues."""
    warnings = _extract_warning_blocks(output)
    issues: list[DiagnosticIssue] = []

    for warning in warnings:
        issue = _issue_from_warning(warning, project_root=project_root)

        if issue is not None:
            issues.append(issue)

    return issues


def _extract_warning_blocks(output: str) -> list[str]:
    """Extract warning/error blocks from MkDocs output.

    MkDocs and mkdocstrings may emit continuation lines after the initial
    WARNING/ERROR line. This keeps those continuation lines attached.
    """
    blocks: list[str] = []
    current: list[str] = []

    for line in output.splitlines():
        if MKDOCS_WARNING_PATTERN.match(line):
            if current:
                blocks.append("\n".join(current).strip())
            current = [line]
            continue

        if current and line.strip():
            current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return blocks


def _issue_from_warning(
    warning: str,
    *,
    project_root: Path,
) -> DiagnosticIssue | None:
    match = MKDOCS_WARNING_PATTERN.match(warning.splitlines()[0])

    if match is None:
        return None

    message = match.group("message").strip()
    full_message = warning.replace("\n", " ").strip()
    code = _classify_mkdocs_warning(full_message)
    severity = _severity_for_code(code)

    file_path, line_number = _extract_location(full_message, project_root=project_root)

    return DiagnosticIssue(
        source="MkDocs",
        code=code,
        severity=severity,
        category="MkDocs",
        message=message,
        file_path=file_path,
        line_number=line_number,
    )


def _classify_mkdocs_warning(message: str) -> str:
    normalized = message.lower()

    typing_tokens = [
        "type annotation",
        "annotation",
        "typing",
        "type hints",
        "missing type",
    ]

    if any(token in normalized for token in typing_tokens):
        return "TYPING"

    docformat_tokens = [
        "docstring",
        "parameter",
        "parameters",
        "return",
        "returns",
        "signature",
        "documented",
    ]

    if any(token in normalized for token in docformat_tokens):
        return "DOCFORMAT"

    return "FALLBACK"


def _severity_for_code(code: str) -> IssueSeverity:
    if code == "TYPING":
        return "todo"

    if code == "DOCFORMAT":
        return "fixme"

    return "warning"


def _extract_location(
    message: str,
    *,
    project_root: Path,
) -> tuple[Path | None, int | None]:
    match = PYTHON_PATH_PATTERN.search(message)

    if match is None:
        return None, None

    raw_path = match.group("path")
    raw_line = match.group("line")

    candidate = Path(raw_path)
    file_path = candidate if candidate.is_absolute() else project_root / candidate

    line_number = int(raw_line) if raw_line is not None else None

    return file_path, line_number


def _combined_output(stdout: str | None, stderr: str | None) -> str:
    parts: list[str] = []

    if stdout:
        parts.append(stdout)

    if stderr:
        parts.append(stderr)

    return "\n".join(parts)
