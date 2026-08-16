"""MkDocs navigation helpers for coverage reports."""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.core.markers import replace_between_markers

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console

type JsonObject = dict[str, object]
type Tree = dict[str, Tree | str]


@dataclass(frozen=True, slots=True)
class CoverageNavItem:
    """Single coverage HTML page entry."""

    source_path: str
    html_path: Path


def update_coverage_nav(cfg: DocToolsConfig, console: Console) -> None:
    """Update the generated Coverage navigation block in mkdocs.yml."""
    if cfg.coverage is None:
        msg = "coverage"
        raise MissingConfigSectionError(msg)

    if not cfg.coverage.nav_enabled:
        return

    output_dir = _coverage_output_dir(cfg)
    page_file = _coverage_page_file(cfg)

    nav_block = build_coverage_nav_block(
        docs_src_dir=cfg.docs_src_dir,
        output_dir=output_dir,
        page_file=page_file,
        max_depth=cfg.coverage.nav_max_depth,
    )

    replace_between_markers(
        file_path=cfg.mkdocs_config,
        start_marker=cfg.coverage.nav_start_marker,
        end_marker=cfg.coverage.nav_end_marker,
        new_block=nav_block,
    )

    console.ok("Coverage navigation updated in mkdocs.yml")


def build_coverage_nav_block(
    *,
    docs_src_dir: Path,
    output_dir: Path,
    page_file: Path,
    max_depth: int,
) -> str:
    """Build a MkDocs YAML navigation block for a coverage report."""
    lines: list[str] = []

    overview_link = _docs_relative_link(docs_src_dir, page_file)
    lines.append(f"- Overview: {overview_link}")

    index_file = _first_existing(output_dir, ["covindex.html", "index.html"])
    if index_file is not None:
        index_link = _docs_relative_link(docs_src_dir, index_file)
        lines.append(f"- HTML index: {index_link}")

    class_index = output_dir / "class_index.html"
    if class_index.exists():
        class_link = _docs_relative_link(docs_src_dir, class_index)
        lines.append(f"- Class index: {class_link}")

    function_index = output_dir / "function_index.html"
    if function_index.exists():
        function_link = _docs_relative_link(docs_src_dir, function_index)
        lines.append(f"- Function index: {function_link}")

    items = read_coverage_nav_items(output_dir)
    if items:
        tree = build_coverage_tree(
            items,
            docs_src_dir=docs_src_dir,
            max_depth=max_depth,
        )
        rendered_tree = render_tree(tree, indent=2)
        if rendered_tree:
            lines.append("- Files:")
            lines.extend(rendered_tree)

    return "\n".join(lines)


def read_coverage_nav_items(output_dir: Path) -> list[CoverageNavItem]:
    """Read coverage navigation items from coverage.py status.json.

    Falls back to an empty list when the status file is missing or unsupported.
    """
    status_file = output_dir / "status.json"
    if not status_file.exists():
        return []

    try:
        raw = json.loads(status_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(raw, dict):
        return []

    files_raw = raw.get("files")
    if not isinstance(files_raw, dict):
        return []

    items: list[CoverageNavItem] = []

    for key, value in files_raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue

        typed_value = _object_dict(value)
        source_path = _extract_source_path(key, typed_value)
        html_filename = _extract_html_filename(typed_value)

        if source_path is None or html_filename is None:
            continue

        html_path = output_dir / html_filename
        if not html_path.exists():
            continue

        items.append(
            CoverageNavItem(
                source_path=_normalize_source_path(source_path),
                html_path=html_path,
            ),
        )

    return sorted(items, key=lambda item: item.source_path)


def build_coverage_tree(
    items: list[CoverageNavItem],
    *,
    docs_src_dir: Path,
    max_depth: int,
) -> Tree:
    """Build a nested tree from coverage items."""
    tree: Tree = {}

    for item in items:
        parts = _bounded_parts(item.source_path, max_depth=max_depth)
        if not parts:
            continue

        link = _docs_relative_link(docs_src_dir, item.html_path)
        _insert_tree_item(tree, parts, link)

    return tree


def render_tree(tree: Tree, *, indent: int = 0) -> list[str]:
    """Render a nested tree as MkDocs YAML nav lines."""
    lines: list[str] = []
    prefix = " " * indent

    for key in sorted(tree):
        value = tree[key]
        if isinstance(value, str):
            lines.append(f"{prefix}- {key}: {value}")
        else:
            lines.append(f"{prefix}- {key}:")
            lines.extend(render_tree(value, indent=indent + 4))

    return lines


def inject_coverage_backlinks(cfg: DocToolsConfig, console: Console) -> None:
    """Inject a lightweight backlink into generated coverage HTML pages."""
    if cfg.coverage is None:
        msg = "coverage"
        raise MissingConfigSectionError(msg)

    if not cfg.coverage.inject_backlinks:
        return

    output_dir = _coverage_output_dir(cfg)
    page_file = _coverage_page_file(cfg)

    if not output_dir.exists():
        return

    changed = 0

    for html_file in output_dir.glob("*.html"):
        if _inject_backlink_into_file(
            html_file=html_file,
            target_page=page_file,
            label=cfg.coverage.backlink_label,
        ):
            changed += 1

    if changed:
        console.ok(f"Coverage backlinks injected into {changed} HTML files")


def _inject_backlink_into_file(
    *,
    html_file: Path,
    target_page: Path,
    label: str,
) -> bool:
    content = html_file.read_text(encoding="utf-8")
    marker = "py-doc-tools-coverage-backlink"

    if marker in content:
        return False

    href = _coverage_html_runtime_link(html_file, target_page)

    backlink = (
        f'<div class="{marker}" '
        'style="padding:8px 12px; background:#f5f5f5; '
        'border-bottom:1px solid #ddd; font-family:sans-serif;">'
        f'<a href="{href}">{label}</a>'
        "</div>"
    )

    if "<body>" in content:
        updated = content.replace("<body>", f"<body>\n{backlink}", 1)
    elif "<body " in content:
        body_start = content.find("<body ")
        body_end = content.find(">", body_start)
        if body_end == -1:
            return False

        updated = content[: body_end + 1] + "\n" + backlink + content[body_end + 1 :]
    else:
        return False

    _ = html_file.write_text(updated, encoding="utf-8")
    return True


def _extract_source_path(key: str, value: JsonObject) -> str | None:
    for field_name in ("relative_filename", "filename", "source", "path"):
        candidate = value.get(field_name)
        if isinstance(candidate, str) and candidate:
            return candidate

    return key


def _extract_html_filename(value: JsonObject) -> str | None:
    for field_name in ("html_filename", "html_file", "html", "index"):
        candidate = value.get(field_name)
        if isinstance(candidate, str) and candidate:
            return candidate

    return None


def _normalize_source_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _bounded_parts(source_path: str, *, max_depth: int) -> list[str]:
    parts = [part for part in source_path.split("/") if part]

    if max_depth <= 0 or len(parts) <= max_depth:
        return parts

    return ["...", *parts[-max_depth:]]


def _insert_tree_item(tree: Tree, parts: list[str], link: str) -> None:
    current = tree

    for part in parts[:-1]:
        existing = current.get(part)
        if not isinstance(existing, dict):
            existing = {}
            current[part] = existing
        current = existing

    current[parts[-1]] = link


def _docs_relative_link(docs_src_dir: Path, target_file: Path) -> str:
    return posixpath.relpath(
        target_file.as_posix(),
        start=docs_src_dir.as_posix(),
    )


def _coverage_html_runtime_link(html_file: Path, target_page: Path) -> str:
    """Build a link from a generated coverage HTML file back to a MkDocs page.

    MkDocs serves Markdown files as directory URLs by default.

    Example:
        docs/coverage-report.md -> coverage-report/

    Therefore, backlinks injected into raw coverage HTML files should include
    the trailing slash to avoid MkDocs redirecting with HTTP 302.
    """
    page_url_dir = target_page.with_suffix("")
    href = posixpath.relpath(
        page_url_dir.as_posix(),
        start=html_file.parent.as_posix(),
    )

    return f"{href}/"

def _first_existing(directory: Path, filenames: list[str]) -> Path | None:
    for filename in filenames:
        candidate = directory / filename
        if candidate.exists():
            return candidate

    return None


def _coverage_output_dir(cfg: DocToolsConfig) -> Path:
    if cfg.coverage is None:
        msg = "coverage"
        raise MissingConfigSectionError(msg)

    if cfg.coverage.output_dir is not None:
        return cfg.coverage.output_dir

    return cfg.docs_src_dir / "coverage"


def _coverage_page_file(cfg: DocToolsConfig) -> Path:
    if cfg.coverage is None:
        msg = "coverage"
        raise MissingConfigSectionError(msg)

    if cfg.coverage.page_file is not None:
        return cfg.coverage.page_file

    return cfg.docs_src_dir / "coverage-report.md"


def _object_dict(value: dict[object, object]) -> JsonObject:
    result: JsonObject = {}

    for key, item in value.items():
        if isinstance(key, str):
            result[key] = item

    return result
