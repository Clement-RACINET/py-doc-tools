"""TODO/FIXME documentation generator."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


@dataclass(frozen=True, slots=True)
class TodoItem:
    """A TODO-like marker found in source files."""

    marker: str
    file_path: Path
    line_number: int
    text: str


def generate_todo_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Generate a Markdown page listing TODO/FIXME markers."""
    if cfg.todo is None:
        msg = "todo"
        raise MissingConfigSectionError(msg)

    items = collect_todo_items(cfg)
    cfg.todo.output_file.parent.mkdir(parents=True, exist_ok=True)

    _ = cfg.todo.output_file.write_text(
        _render_todo_markdown(cfg, items),
        encoding="utf-8",
    )

    console.ok(f"TODO documentation generated: {cfg.todo.output_file}")
    return 0


def collect_todo_items(cfg: DocToolsConfig) -> list[TodoItem]:
    """Collect TODO-like markers from configured scan roots."""
    if cfg.todo is None:
        msg = "todo"
        raise MissingConfigSectionError(msg)

    items: list[TodoItem] = []

    for root in cfg.todo.scan_roots:
        if not root.exists():
            continue

        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue

            if _should_skip(
                file_path=file_path,
                root=root,
                exclude_dirs=cfg.todo.exclude_dirs,
                exclude_files=cfg.todo.exclude_files,
            ):
                continue

            items.extend(_scan_file(file_path, cfg.todo.markers))

    return items


def _scan_file(file_path: Path, markers: list[str]) -> list[TodoItem]:
    items: list[TodoItem] = []

    try:
        lines = file_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return items

    for index, line in enumerate(lines, start=1):
        for marker in markers:
            token = f"{marker}:"
            if token not in line:
                continue

            text = line.split(token, maxsplit=1)[1].strip()
            items.append(
                TodoItem(
                    marker=marker,
                    file_path=file_path,
                    line_number=index,
                    text=text,
                ),
            )

    return items


def _render_todo_markdown(
    cfg: DocToolsConfig,
    items: list[TodoItem],
) -> str:
    lines = ["# TODO / FIXME", ""]

    if not items:
        lines.extend(["No TODO-like markers found.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| Marker | File | Line | Text |",
            "|---|---|---:|---|",
        ],
    )

    for item in items:
        relative = item.file_path.relative_to(cfg.project_root).as_posix()
        escaped_text = item.text.replace("|", "\\|")
        lines.append(
            f"| `{item.marker}` | `{relative}` | {item.line_number} | {escaped_text} |",
        )

    lines.append("")
    return "\n".join(lines)


def _should_skip(
    *,
    file_path: Path,
    root: Path,
    exclude_dirs: list[str],
    exclude_files: list[str],
) -> bool:
    relative_parts = file_path.relative_to(root).parts

    for part in relative_parts[:-1]:
        if part in exclude_dirs:
            return True

    return any(fnmatch.fnmatch(file_path.name, pattern) for pattern in exclude_files)
