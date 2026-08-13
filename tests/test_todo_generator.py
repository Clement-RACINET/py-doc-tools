"""Tests for TODO/FIXME documentation generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools.config.model import DocToolsConfig, TodoConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.todo.generator import collect_todo_items, generate_todo_docs

if TYPE_CHECKING:
    from pathlib import Path


def _base_config(tmp_path: Path, todo: TodoConfig | None) -> DocToolsConfig:
    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_todo=todo is not None,
        todo=todo,
    )


def test_generate_todo_docs_with_items(tmp_path: Path) -> None:
    """TODO generator writes a Markdown table with markers."""
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "module.py").write_text(
        "# TODO: improve this\n# FIXME: fix that\n",
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "todo.md"
    cfg = _base_config(
        tmp_path,
        TodoConfig(
            output_file=output,
            scan_roots=[src],
            markers=["TODO", "FIXME"],
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    code = generate_todo_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "| Marker | File | Line | Text |" in content
    assert "`TODO`" in content
    assert "`FIXME`" in content
    assert "improve this" in content
    assert "fix that" in content


def test_generate_todo_docs_without_items(tmp_path: Path) -> None:
    """TODO generator reports when no markers are found."""
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "module.py").write_text("print('hello')\n", encoding="utf-8")

    output = tmp_path / "docs" / "todo.md"
    cfg = _base_config(
        tmp_path,
        TodoConfig(
            output_file=output,
            scan_roots=[src],
            markers=["TODO"],
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    code = generate_todo_docs(cfg, Console())

    assert code == 0
    assert "No TODO-like markers found." in output.read_text(encoding="utf-8")


def test_collect_todo_items_skips_excluded_paths(tmp_path: Path) -> None:
    """TODO collector respects excluded dirs and file patterns."""
    src = tmp_path / "src"
    ignored = src / "__pycache__"
    src.mkdir()
    ignored.mkdir()

    _ = (src / "keep.py").write_text("# TODO: keep\n", encoding="utf-8")
    _ = (src / "skip.txt").write_text("# TODO: skip file\n", encoding="utf-8")
    _ = (ignored / "skip.py").write_text("# TODO: skip dir\n", encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        TodoConfig(
            output_file=tmp_path / "docs" / "todo.md",
            scan_roots=[src],
            markers=["TODO"],
            exclude_dirs=["__pycache__"],
            exclude_files=["*.txt"],
        ),
    )

    items = collect_todo_items(cfg)

    assert len(items) == 1
    assert items[0].text == "keep"


def test_collect_todo_items_ignores_missing_roots(tmp_path: Path) -> None:
    """TODO collector ignores missing scan roots."""
    cfg = _base_config(
        tmp_path,
        TodoConfig(
            output_file=tmp_path / "docs" / "todo.md",
            scan_roots=[tmp_path / "missing"],
            markers=["TODO"],
            exclude_dirs=[],
            exclude_files=[],
        ),
    )

    assert collect_todo_items(cfg) == []


def test_generate_todo_docs_missing_config(tmp_path: Path) -> None:
    """Missing todo config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="todo"):
        _ = generate_todo_docs(cfg, Console())


def test_collect_todo_items_missing_config(tmp_path: Path) -> None:
    """Missing todo config raises in collector too."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="todo"):
        _ = collect_todo_items(cfg)
