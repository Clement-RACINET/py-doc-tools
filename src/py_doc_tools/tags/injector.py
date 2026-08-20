"""Source tag injection from normalized diagnostic issues."""

from __future__ import annotations

import ast
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
    """Inject issue tags into one Python source file.

    Args:
        file_path: Python source file to update.
        issues: Diagnostic issues localized in the file.
        prefix: Generated tag prefix.
        dry_run: If ``True``, compute insertions without writing the file.

    Returns:
        Number of injected tags.

    Raises:
        No exception is intentionally propagated. Unreadable files are skipped to
        keep diagnostics generation robust.
    """
    if not file_path.exists():
        return 0

    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError:
        return 0

    lines = source.splitlines(keepends=True)
    docstring_ranges = _collect_docstring_ranges(source)
    insertions: dict[int, list[str]] = defaultdict(list)

    for issue in sorted(
        issues,
        key=lambda item: (item.line_number or 1, item.code, item.message),
    ):
        line_number = issue.line_number or 1
        requested_index = max(0, min(line_number - 1, len(lines)))
        index = _safe_insertion_index(
            requested_index=requested_index,
            docstring_ranges=docstring_ranges,
        )
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


def _collect_docstring_ranges(source: str) -> list[tuple[int, int]]:
    """Collect line ranges occupied by module, class, and function docstrings.

    Args:
        source: Python source code.

    Returns:
        List of inclusive-exclusive line ranges as zero-based indexes. Each
        range is ``(start_index, end_index)``.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    ranges: list[tuple[int, int]] = []

    module_range = _docstring_range_from_body(tree.body)
    if module_range is not None:
        ranges.append(module_range)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            node_range = _docstring_range_from_body(node.body)
            if node_range is not None:
                ranges.append(node_range)

    return ranges


def _docstring_range_from_body(body: list[ast.stmt]) -> tuple[int, int] | None:
    """Return the docstring line range for an AST body, if any.

    Args:
        body: AST statement body of a module, class, or function.

    Returns:
        Inclusive-exclusive zero-based line range of the docstring, or ``None``
        when the body has no docstring.
    """
    if not body:
        return None

    first = body[0]

    if not isinstance(first, ast.Expr):
        return None

    value = first.value

    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return None

    end_line = first.end_lineno
    if end_line is None:
        return None

    start_index = max(0, first.lineno - 1)
    end_index = max(start_index + 1, end_line)

    return start_index, end_index


def _safe_insertion_index(
    *,
    requested_index: int,
    docstring_ranges: list[tuple[int, int]],
) -> int:
    """Return a safe insertion index outside Python docstrings.

    Args:
        requested_index: Zero-based target insertion index.
        docstring_ranges: Inclusive-exclusive zero-based docstring ranges.

    Returns:
        ``requested_index`` when it is outside a docstring, otherwise the start
        index of the containing docstring.
    """
    for start_index, end_index in docstring_ranges:
        if start_index <= requested_index < end_index:
            return start_index

    return requested_index


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
