"""Optional source tag injection."""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


def inject_source_tags(cfg: DocToolsConfig, console: Console) -> int:
    """Inject source tags near TODO-like markers."""
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    changed_files = 0

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

            if _process_file(cfg, file_path):
                changed_files += 1

    if cfg.tags.dry_run:
        console.info(
            f"Tag dry-run completed. Files that would change: {changed_files}",
        )
    else:
        console.ok(f"Source tags injected. Changed files: {changed_files}")

    return 0


def _process_file(cfg: DocToolsConfig, file_path: Path) -> bool:
    if cfg.tags is None:
        msg = "tags"
        raise MissingConfigSectionError(msg)

    original = file_path.read_text(encoding="utf-8")
    lines = original.splitlines()

    new_lines: list[str] = []
    changed = False

    for line in lines:
        if _contains_marker(line, cfg.tags.markers):
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}{cfg.tags.start_token}")
            new_lines.append(line)
            new_lines.append(f"{indent}{cfg.tags.end_token}")
            changed = True
        else:
            new_lines.append(line)

    if not changed:
        return False

    if not cfg.tags.dry_run:
        _ = file_path.write_text(
            "\n".join(new_lines) + "\n",
            encoding="utf-8",
        )

    return True


def _contains_marker(line: str, markers: list[str]) -> bool:
    return any(f"{marker}:" in line for marker in markers)


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
