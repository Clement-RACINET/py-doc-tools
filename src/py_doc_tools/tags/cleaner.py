"""Generated source tag cleanup."""

from __future__ import annotations

import fnmatch
import re
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


PY_DOC_TOOLS_TAG_PATTERN = re.compile(
    r"^\s*#\s*(?:TODO|FIXME)\[py-doc-tools:[^\]]+\]:.*$",
    re.IGNORECASE,
)

LEGACY_TAG_PATTERNS = [
    re.compile(r"^\s*#\s*FIXME\[Ruff:[^\]]+\]:.*$", re.IGNORECASE),
    re.compile(r"^\s*#\s*FIXME\[BasedPyright:[^\]]+\]:.*$", re.IGNORECASE),
    re.compile(r"^\s*#\s*(?:TODO|FIXME)\s*\[MKDOC\]\s*\[[^\]]+\].*$", re.IGNORECASE),
    re.compile(r"^\s*#\s*(?:TODO|FIXME)\s*\[MkDocs:[^\]]+\]:.*$", re.IGNORECASE),
]


def clean_generated_source_tags(cfg: DocToolsConfig, console: Console) -> int:
    """Remove generated source tags from configured scan roots."""
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    changed_files = 0
    removed_tags = 0

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

            removed = clean_generated_tags_in_file(
                file_path,
                clean_legacy=cfg.tags.clean_legacy,
            )

            if removed > 0:
                changed_files += 1
                removed_tags += removed

    message = (
        f"Generated source tags cleaned: {removed_tags} tag(s) "
        f"in {changed_files} file(s)."
    )
    console.ok(message)

    return 0


def clean_generated_tags_in_file(file_path: Path, *, clean_legacy: bool = True) -> int:
    """Remove generated tags in a single source file.

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
        if _is_generated_tag(line, clean_legacy=clean_legacy):
            removed += 1
            continue

        kept.append(line)

    if removed == 0:
        return 0

    _ = file_path.write_text("".join(kept), encoding="utf-8")
    return removed


def _is_generated_tag(line: str, *, clean_legacy: bool) -> bool:
    if PY_DOC_TOOLS_TAG_PATTERN.search(line):
        return True

    if not clean_legacy:
        return False

    return any(pattern.search(line) for pattern in LEGACY_TAG_PATTERNS)


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
