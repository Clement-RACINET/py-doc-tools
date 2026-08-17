"""TODO/FIXME documentation generator with AUTOGEN sections."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from datetime import UTC, datetime
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
    section: str


TAG_TO_SECTION: dict[str, str] = {
    "BUG": "GENERAL_BUG",
    "HACK": "GENERAL_HACK",
    "FIXME": "GENERAL_FIXME",
    "TODO": "GENERAL_TODO",
    "BREAKING": "BREAKING",
    "WARN": "GENERAL_FALLBACK",
}

GENERATED_TAG_PATTERN = re.compile(
    r"#\s*(?P<marker>TODO|FIXME)\[py-doc-tools:(?P<source>[^:\]]+):(?P<code>[^\]]+)\]:\s*(?P<message>.*)$",
    re.IGNORECASE,
)

LEGACY_MKDOC_TAG_PATTERN = re.compile(
    r"#\s*(?P<marker>TODO|FIXME)\s*\[MKDOC\]\s*\[(?P<category>[A-Z_]+)\]\s*(?P<message>.*)$",
    re.IGNORECASE,
)

GENERAL_TAG_PATTERN = re.compile(
    r"#\s*(?P<marker>TODO|FIXME|BUG|HACK|WARN|BREAKING)\b(?!\[py-doc-tools:)(?!\s*\[MKDOC\])\s*[:\-\u2013]?\s*(?P<message>.*)$",
    re.IGNORECASE,
)

EMPTY_MESSAGE: dict[str, str] = {
    "BREAKING": "> *Aucune tâche cassante détectée.*",
    "GENERAL_BUG": "> *Aucun BUG référencé.*",
    "GENERAL_HACK": "> *Aucun HACK temporaire détecté.*",
    "GENERAL_FIXME": "> *Aucun FIXME en suspens détecté.*",
    "GENERAL_TODO": "> *Aucun TODO en suspens détecté.*",
    "GENERAL_FALLBACK": "> *Aucune autre tâche détectée.*",
    "RUFF": "> *Aucun problème Ruff détecté.*",
    "BASEDPYRIGHT": "> *Aucun problème BasedPyright détecté.*",
    "PYTEST": "> *Aucun échec pytest détecté.*",
    "MKDOCS_TYPING": "> *Aucun problème de typage documentaire détecté.*",
    "MKDOCS_DOCFORMAT": "> *Aucune docstring non conforme détectée.*",
    "MKDOCS_FALLBACK": "> *Aucun warning MkDocs non localisé détecté.*",
}


def generate_todo_docs(cfg: DocToolsConfig, console: Console) -> int:
    """Generate or update TODO/FIXME documentation."""
    if cfg.todo is None:
        msg = "todo"
        raise MissingConfigSectionError(msg)

    items = collect_todo_items(cfg)
    cfg.todo.output_file.parent.mkdir(parents=True, exist_ok=True)

    if cfg.todo.mode == "table":
        content = _render_todo_table(cfg, items)
    else:
        content = _render_or_update_sections(cfg, items)

    _ = cfg.todo.output_file.write_text(
        content,
        encoding="utf-8",
        newline="\n",
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

    allowed_markers = {marker.upper() for marker in markers}

    for index, line in enumerate(lines, start=1):
        generated = GENERATED_TAG_PATTERN.search(line)
        if generated:
            marker = generated.group("marker").upper()
            source = generated.group("source").upper()
            code = generated.group("code")
            message = generated.group("message").strip()

            if marker not in allowed_markers:
                continue

            section = _section_for_generated_issue(source, code)
            items.append(
                TodoItem(
                    marker=marker,
                    file_path=file_path,
                    line_number=index,
                    text=f"[{source}:{code}] {message}",
                    section=section,
                ),
            )
            continue

        legacy_mkdoc = LEGACY_MKDOC_TAG_PATTERN.search(line)
        if legacy_mkdoc:
            marker = legacy_mkdoc.group("marker").upper()
            category = legacy_mkdoc.group("category").upper()
            message = legacy_mkdoc.group("message").strip()

            if marker not in allowed_markers:
                continue

            section = _section_for_mkdocs_category(category)
            items.append(
                TodoItem(
                    marker=marker,
                    file_path=file_path,
                    line_number=index,
                    text=message,
                    section=section,
                ),
            )
            continue

        general = GENERAL_TAG_PATTERN.search(line)
        if general:
            marker = general.group("marker").upper()
            message = general.group("message").strip() or "(pas de description)"

            if marker not in allowed_markers:
                continue

            items.append(
                TodoItem(
                    marker=marker,
                    file_path=file_path,
                    line_number=index,
                    text=message,
                    section=TAG_TO_SECTION.get(marker, "GENERAL_FALLBACK"),
                ),
            )

    return items


def _section_for_generated_issue(source: str, code: str) -> str:
    """Return the TODO section for a generated diagnostic issue."""
    normalized_source = source.upper()
    normalized_code = code.upper()

    direct_sections = {
        "RUFF": "RUFF",
        "BASEDPYRIGHT": "BASEDPYRIGHT",
        "PYRIGHT": "BASEDPYRIGHT",
        "PYTEST": "PYTEST",
    }

    if normalized_source in direct_sections:
        return direct_sections[normalized_source]

    mkdocs_sections = {
        "TYPING": "MKDOCS_TYPING",
        "DOCFORMAT": "MKDOCS_DOCFORMAT",
    }

    if normalized_source in {"MKDOCS", "MKDOC"}:
        return mkdocs_sections.get(normalized_code, "MKDOCS_FALLBACK")

    return "GENERAL_FALLBACK"


def _section_for_mkdocs_category(category: str) -> str:
    normalized = category.upper()

    if normalized == "TYPING":
        return "MKDOCS_TYPING"

    if normalized == "DOCFORMAT":
        return "MKDOCS_DOCFORMAT"

    return "MKDOCS_FALLBACK"


def _render_or_update_sections(cfg: DocToolsConfig, items: list[TodoItem]) -> str:
    if cfg.todo is None:
        msg = "todo"
        raise MissingConfigSectionError(msg)

    sections = _group_by_section(cfg, items)

    if cfg.todo.output_file.exists() and cfg.todo.preserve_manual_content:
        content = cfg.todo.output_file.read_text(encoding="utf-8")
    else:
        content = _default_todo_template()

    content = _update_date(content)

    for section in _all_sections():
        content = _replace_or_append_section(
            content,
            section,
            sections.get(section, []),
        )

    return content.rstrip() + "\n"


def _group_by_section(
    cfg: DocToolsConfig,
    items: list[TodoItem],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {section: [] for section in _all_sections()}

    for item in items:
        relative = item.file_path.relative_to(cfg.project_root).as_posix()
        text = item.text.replace("\n", " ").strip()
        grouped.setdefault(item.section, []).append(
            f"- `{relative}:{item.line_number}` — {text}",
        )

    return grouped


def _all_sections() -> list[str]:
    return [
        "BREAKING",
        "GENERAL_BUG",
        "GENERAL_HACK",
        "GENERAL_FIXME",
        "GENERAL_TODO",
        "GENERAL_FALLBACK",
        "RUFF",
        "BASEDPYRIGHT",
        "PYTEST",
        "MKDOCS_TYPING",
        "MKDOCS_DOCFORMAT",
        "MKDOCS_FALLBACK",
    ]


def _default_todo_template() -> str:
    lines = [
        "# TODO",
        "",
        "Dernière mise à jour : <!-- AUTOGEN:DATE -->",
        "",
    ]

    for section in _all_sections():
        lines.extend(
            [
                f"## {section}",
                "",
                f"<!-- AUTOGEN:{section}:START -->",
                EMPTY_MESSAGE.get(section, "> *Aucun élément.*"),
                f"<!-- AUTOGEN:{section}:END -->",
                "",
            ],
        )

    return "\n".join(lines)


def _update_date(content: str) -> str:
    date_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    if "<!-- AUTOGEN:DATE -->" in content:
        return re.sub(
            r"<!--\s*AUTOGEN:DATE\s*-->(?:\s*\*[^*]*\*)?",
            f"<!-- AUTOGEN:DATE --> *{date_str}*",
            content,
        )

    return content


def _replace_or_append_section(
    content: str,
    section: str,
    lines: list[str],
) -> str:
    start_marker = f"<!-- AUTOGEN:{section}:START -->"
    end_marker = f"<!-- AUTOGEN:{section}:END -->"
    empty_message = EMPTY_MESSAGE.get(section, "> *Aucun élément.*")
    body = "\n".join(lines) if lines else empty_message

    if start_marker in content and end_marker in content:
        pattern = re.compile(
            rf"({re.escape(start_marker)})\n.*?({re.escape(end_marker)})",
            re.DOTALL,
        )
        return pattern.sub(
            lambda _: f"{start_marker}\n{body}\n{end_marker}",
            content,
        )

    addition = "\n".join(
        [
            "",
            f"## {section}",
            "",
            start_marker,
            body,
            end_marker,
            "",
        ],
    )

    return content.rstrip() + "\n" + addition


def _render_todo_table(
    cfg: DocToolsConfig,
    items: list[TodoItem],
) -> str:
    lines = ["# TODO / FIXME", ""]

    if not items:
        lines.extend(["No TODO-like markers found.", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| Section | Marker | File | Line | Text |",
            "|---|---|---|---:|---|",
        ],
    )

    for item in items:
        relative = item.file_path.relative_to(cfg.project_root).as_posix()
        escaped_text = item.text.replace("|", "\\|")
        row = (
            f"| `{item.section}` | `{item.marker}` | `{relative}` | "
            f"{item.line_number} | {escaped_text} |"
        )
        lines.append(row)

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
