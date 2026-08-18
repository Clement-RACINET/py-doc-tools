"""Source tag injection from normalized diagnostic issues."""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.tags.generated import render_generated_tag

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console
    from py_doc_tools.issues.model import DiagnosticIssue


def inject_source_tags(cfg: DocToolsConfig, console: Console) -> int:
    """CLI-compatible source tag injection entry point.

    Run diagnostics collection and inject generated source tags when source tag
    injection is enabled in the diagnostics configuration.
    """
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    if cfg.diagnostics is None:
        msg = "diagnostics"
        raise MissingConfigSectionError(msg)

    if not cfg.diagnostics.inject_source_tags:
        message = (
            "Source tag injection was requested, but it is disabled by "
            "configuration: "
            "`[tool.py-doc-tools.diagnostics].inject_source_tags = false`. "
            "No source tags were injected."
        )
        console.warn(message)
        return 0

    from py_doc_tools.diagnostics.generator import (  # noqa: PLC0415
        generate_diagnostics_docs,
    )

    return generate_diagnostics_docs(cfg, console)



def inject_issues(
    cfg: DocToolsConfig,
    console: Console,
    issues: list[DiagnosticIssue],
) -> int:
    """Inject generated source tags for localized diagnostic issues."""
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    localized = [issue for issue in issues if issue.is_localized()]
    by_file: dict[Path, list[DiagnosticIssue]] = defaultdict(list)

    for issue in localized:
        if issue.file_path is None:
            continue

        if _is_allowed_file(cfg, issue.file_path):
            by_file[issue.file_path].append(issue)

    changed_files = 0
    injected_tags = 0

    for file_path, file_issues in by_file.items():
        count = inject_issues_in_file(
            file_path=file_path,
            issues=file_issues,
            prefix=cfg.tags.generated_prefix,
            dry_run=cfg.tags.dry_run,
        )

        if count > 0:
            changed_files += 1
            injected_tags += count

    if cfg.tags.dry_run:
        message = (
            "Source tag dry-run completed. Tags that would be injected: "
            f"{injected_tags}."
        )
        console.info(message)
    else:
        message = (
            f"Source diagnostic tags injected: {injected_tags} tag(s) "
            f"in {changed_files} file(s)."
        )
        console.ok(message)

    return 0


def inject_issues_in_file(
    *,
    file_path: Path,
    issues: list[DiagnosticIssue],
    prefix: str,
    dry_run: bool,
) -> int:
    """Inject issue tags into one Python source file."""
    if not file_path.exists():
        return 0

    try:
        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return 0

    insertions: dict[int, list[str]] = defaultdict(list)

    for issue in sorted(
        issues,
        key=lambda item: (item.line_number or 1, item.code, item.message),
    ):
        line_number = issue.line_number or 1
        index = max(0, min(line_number - 1, len(lines)))
        indent = _indent_for_index(lines, index)
        tag = render_generated_tag(issue, prefix=prefix)
        rendered_line = f"{indent}{tag}\n"

        if rendered_line not in insertions[index]:
            insertions[index].append(rendered_line)

    if not insertions:
        return 0

    new_lines: list[str] = []
    injected = 0

    for index, line in enumerate(lines):
        pending = insertions.get(index, [])

        if pending:
            new_lines.extend(pending)
            injected += len(pending)

        new_lines.append(line)

    end_insertions = insertions.get(len(lines), [])
    if end_insertions:
        new_lines.extend(end_insertions)
        injected += len(end_insertions)

    if injected == 0:
        return 0

    if not dry_run:
        _ = file_path.write_text("".join(new_lines), encoding="utf-8")

    return injected


def _indent_for_index(lines: list[str], index: int) -> str:
    if not lines:
        return ""

    safe_index = min(index, len(lines) - 1)
    line = lines[safe_index]
    return line[: len(line) - len(line.lstrip())]


def _is_allowed_file(cfg: DocToolsConfig, file_path: Path) -> bool:
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    if file_path.suffix != ".py":
        return False

    for root in cfg.tags.scan_roots:
        try:
            relative = file_path.relative_to(root)
        except ValueError:
            continue

        if any(part in cfg.tags.exclude_dirs for part in relative.parts[:-1]):
            return False

        return not any(
            fnmatch.fnmatch(file_path.name, pattern)
            for pattern in cfg.tags.exclude_files
        )

    return False
