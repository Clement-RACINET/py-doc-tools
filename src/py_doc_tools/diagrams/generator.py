# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Simple class diagram generation using Python AST."""

from __future__ import annotations

import ast
import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from pathlib import Path

    from py_doc_tools.config.model import DocToolsConfig
    from py_doc_tools.core.console import Console


@dataclass(frozen=True, slots=True)
class ClassInfo:
    """Extracted class information."""

    name: str
    module: str
    bases: list[str]


def generate_class_diagram_docs(
    cfg: DocToolsConfig,
    console: Console,
) -> int:
    """Generate a Mermaid class diagram Markdown page."""
    if cfg.diagrams is None:
        msg = "diagrams"
        raise MissingConfigSectionError(msg)

    classes = _collect_classes(cfg)

    cfg.diagrams.output_file.parent.mkdir(parents=True, exist_ok=True)
    _ = cfg.diagrams.output_file.write_text(
        _render_mermaid(cfg.diagrams.title, classes),
        encoding="utf-8",
    )

    console.ok(f"Class diagram generated: {cfg.diagrams.output_file}")
    return 0


def _collect_classes(cfg: DocToolsConfig) -> list[ClassInfo]:
    if cfg.diagrams is None:
        msg = "diagrams"
        raise MissingConfigSectionError(msg)

    classes: list[ClassInfo] = []

    for root in cfg.diagrams.scan_roots:
        if not root.exists():
            continue

        for file_path in sorted(root.rglob("*.py")):
            if _should_skip(
                file_path=file_path,
                root=root,
                exclude_dirs=cfg.diagrams.exclude_dirs,
                exclude_files=cfg.diagrams.exclude_files,
            ):
                continue

            classes.extend(
                _extract_classes(
                    file_path=file_path,
                    root=root,
                    include_private=cfg.diagrams.include_private,
                ),
            )

    return classes


def _extract_classes(
    *,
    file_path: Path,
    root: Path,
    include_private: bool,
) -> list[ClassInfo]:
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    module = ".".join(file_path.relative_to(root).with_suffix("").parts)
    classes: list[ClassInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        if not include_private and node.name.startswith("_"):
            continue

        classes.append(
            ClassInfo(
                name=node.name,
                module=module,
                bases=[_base_name(base) for base in node.bases],
            ),
        )

    return classes


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _base_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr

    if isinstance(node, ast.Subscript):
        return _base_name(node.value)

    return ""


def _render_mermaid(title: str, classes: list[ClassInfo]) -> str:
    lines = [
        f"# {title}",
        "",
        "```mermaid",
        "classDiagram",
    ]

    for class_info in classes:
        safe_name = _safe_mermaid_name(class_info.name)
        lines.append(f"    class {safe_name}")

    for class_info in classes:
        child = _safe_mermaid_name(class_info.name)

        for base in class_info.bases:
            if not base:
                continue

            parent = _safe_mermaid_name(base.split(".")[-1])
            lines.append(f"    {parent} <|-- {child}")

    lines.extend(["```", ""])
    return "\n".join(lines)


def _safe_mermaid_name(name: str) -> str:
    return name.replace(".", "_").replace("-", "_")


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
