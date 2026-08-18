"""Generated source tag cleanup."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.tags.generated import is_generated_tag_line

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


@dataclass(frozen=True, slots=True)
class TagCleanResult:
    """Summary of generated source tag cleanup."""

    files_scanned: int = 0
    files_changed: int = 0
    removed_tags: int = 0
    changed_files: list[Path] = field(default_factory=list)


def clean_generated_source_tags(
    cfg: DocToolsConfig,
    console: Console,
    *,
    dry_run: bool | None = None,
) -> int:
    """Remove generated source tags from configured scan roots.

    Args:
        cfg: Loaded py-doc-tools configuration.
        console: Console logger.
        dry_run: Optional override for ``cfg.tags.dry_run``. When ``None``, the
            configured value is used.

    Returns:
        Process exit code.
    """
    result = clean_generated_source_tags_result(cfg, dry_run=dry_run)

    effective_dry_run = _effective_dry_run(cfg, dry_run=dry_run)

    if effective_dry_run:
        message = (
            "Generated source tag cleanup dry-run completed: "
            f"{result.removed_tags} tag(s) would be removed "
            f"from {result.files_changed} file(s)."
        )
        console.info(message)
    else:
        message = (
            f"Generated source tags cleaned: {result.removed_tags} tag(s) "
            f"in {result.files_changed} file(s)."
        )
        console.ok(message)

    return 0


def clean_generated_source_tags_result(
    cfg: DocToolsConfig,
    *,
    dry_run: bool | None = None,
) -> TagCleanResult:
    """Clean generated source tags and return a structured summary.

    Args:
        cfg: Loaded py-doc-tools configuration.
        dry_run: Optional override for ``cfg.tags.dry_run``.

    Returns:
        Cleanup summary.

    Raises:
        MissingConfigSectionError: If the ``tags`` configuration is missing.
    """
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    effective_dry_run = _effective_dry_run(cfg, dry_run=dry_run)

    files_scanned = 0
    files_changed = 0
    removed_tags = 0
    changed_files: list[Path] = []

    for root in cfg.tags.scan_roots:
        if not root.exists():
            continue

        for file_path in sorted(root.rglob("*.py")):
            if _should_skip(
                file_path=file_path,
                root=root,
                exclude_dirs=cfg.tags.exclude_dirs,
                exclude_files=cfg.tags.exclude_files,
            ):
                continue

            files_scanned += 1

            removed = clean_generated_tags_in_file(
                file_path,
                clean_legacy=cfg.tags.clean_legacy,
                dry_run=effective_dry_run,
            )

            if removed > 0:
                files_changed += 1
                removed_tags += removed
                changed_files.append(file_path)

    return TagCleanResult(
        files_scanned=files_scanned,
        files_changed=files_changed,
        removed_tags=removed_tags,
        changed_files=changed_files,
    )


def clean_generated_tags_in_file(
    file_path: Path,
    *,
    clean_legacy: bool = True,
    dry_run: bool = False,
) -> int:
    """Remove generated tags in a single source file.

    Args:
        file_path: Python source file to clean.
        clean_legacy: If ``True``, remove legacy generated tags too.
        dry_run: If ``True``, report removals without writing the file.

    Returns:
        Number of removed lines.
    """
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return 0

    kept: list[str] = []
    removed = 0

    for line in lines:
        if is_generated_tag_line(line, clean_legacy=clean_legacy):
            removed += 1
            continue

        kept.append(line)

    if removed == 0:
        return 0

    if not dry_run:
        _ = file_path.write_text("".join(kept), encoding="utf-8")

    return removed


def _effective_dry_run(cfg: DocToolsConfig, *, dry_run: bool | None) -> bool:
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    return cfg.tags.dry_run if dry_run is None else dry_run


def _should_skip(
    *,
    file_path: Path,
    root: Path,
    exclude_dirs: list[str],
    exclude_files: list[str],
) -> bool:
    relative_parts = file_path.relative_to(root).parts

    if any(part in exclude_dirs for part in relative_parts[:-1]):
        return True

    return any(fnmatch.fnmatch(file_path.name, pattern) for pattern in exclude_files)
