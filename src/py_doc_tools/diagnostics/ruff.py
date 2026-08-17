"""Ruff diagnostics collection and parsing."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.subprocesses import run_command
from py_doc_tools.issues.model import DiagnosticIssue

if TYPE_CHECKING:
    from py_doc_tools.config.model import DocToolsConfig

JsonObject = dict[str, object]


def build_ruff_json_command(cfg: DocToolsConfig) -> list[str]:
    """Build a Ruff command that emits JSON diagnostics."""
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    targets = _deduplicate_preserving_order(cfg.diagnostics.ruff_targets)
    if not targets:
        targets = ["."]

    command = [
        sys.executable,
        "-m",
        "ruff",
        "check",
        *targets,
        "--output-format",
        "json",
    ]

    for pattern in _ruff_exclude_patterns(cfg):
        command.extend(["--exclude", pattern])

    return command


def collect_ruff_issues(cfg: DocToolsConfig) -> tuple[list[DiagnosticIssue], int, str]:
    """Run Ruff in JSON mode and return normalized issues."""
    command = build_ruff_json_command(cfg)
    proc = run_command(
        command,
        cwd=cfg.project_root,
        check=False,
        capture_output=True,
    )

    raw_output = _combined_output(proc.stdout, proc.stderr)
    issues = parse_ruff_json_output(raw_output, project_root=cfg.project_root)

    return issues, proc.returncode, raw_output


def parse_ruff_json_output(
    output: str,
    *,
    project_root: Path,
) -> list[DiagnosticIssue]:
    """Parse Ruff JSON output into normalized diagnostic issues."""
    stripped = output.strip()

    if not stripped:
        return []

    raw = _loads_json_object(stripped)
    raw_items = _object_list_from_object(raw)

    if raw_items is None:
        return []

    issues: list[DiagnosticIssue] = []

    for item in raw_items:
        item_object = _object_dict_from_object(item)

        if item_object is None:
            continue

        issue = _issue_from_ruff_item(
            item_object,
            project_root=project_root,
        )

        if issue is not None:
            issues.append(issue)

    return issues


def _loads_json_object(value: str) -> object:
    """Load JSON data while preventing Any from leaking into typed code."""
    try:
        return cast("object", json.loads(value))
    except json.JSONDecodeError:
        return None


def _object_list_from_object(value: object) -> list[object] | None:
    """Convert an arbitrary object to a list of objects."""
    if not isinstance(value, list):
        return None

    raw_items = cast("list[object]", value)
    return list(raw_items)


def _object_dict_from_object(value: object) -> JsonObject | None:
    """Convert an arbitrary object to a string-keyed JSON object."""
    if not isinstance(value, dict):
        return None

    raw_dict = cast("dict[object, object]", value)
    result: JsonObject = {}

    for key, item in raw_dict.items():
        if isinstance(key, str):
            result[key] = item

    return result


def _issue_from_ruff_item(
    item: JsonObject,
    *,
    project_root: Path,
) -> DiagnosticIssue | None:
    code = _optional_string(item, "code")
    message = _optional_string(item, "message")
    filename = _optional_string(item, "filename")
    location = _optional_object(item, "location")

    if code is None or message is None:
        return None

    file_path = _file_path_from_filename(filename, project_root=project_root)
    line_number = _optional_int(location, "row") if location is not None else None
    column = _optional_int(location, "column") if location is not None else None

    return DiagnosticIssue(
        source="Ruff",
        code=code,
        severity="fixme",
        category="Ruff",
        message=message,
        file_path=file_path,
        line_number=line_number,
        column=column,
    )


def _file_path_from_filename(
    filename: str | None,
    *,
    project_root: Path,
) -> Path | None:
    if filename is None or not filename:
        return None

    candidate = Path(filename)
    if candidate.is_absolute():
        return candidate

    return project_root / candidate


def _optional_string(table: JsonObject, key: str) -> str | None:
    value = table.get(key)
    return value if isinstance(value, str) else None


def _optional_int(table: JsonObject, key: str) -> int | None:
    value = table.get(key)
    return value if isinstance(value, int) else None


def _optional_object(table: JsonObject, key: str) -> JsonObject | None:
    value = table.get(key)
    return _object_dict_from_object(value)


def _ruff_exclude_patterns(cfg: DocToolsConfig) -> list[str]:
    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    return _deduplicate_preserving_order(
        [
            *cfg.diagnostics.ruff_exclude_dirs,
            *cfg.diagnostics.ruff_exclude_files,
        ],
    )


def _deduplicate_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result


def _combined_output(stdout: str | None, stderr: str | None) -> str:
    parts: list[str] = []

    if stdout:
        parts.append(stdout)

    if stderr:
        parts.append(stderr)

    return "\n".join(parts)
