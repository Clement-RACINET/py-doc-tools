# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for class diagram generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from py_doc_tools.config.model import DiagramsConfig, DocToolsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.diagrams.generator import generate_class_diagram_docs

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _make_config(**kwargs: object) -> DocToolsConfig:
    config_cls = cast("Callable[..., DocToolsConfig]", DocToolsConfig)
    return config_cls(**kwargs)


def _make_diagrams_config(**kwargs: object) -> DiagramsConfig:
    config_cls = cast("Callable[..., DiagramsConfig]", DiagramsConfig)
    return config_cls(**kwargs)


def _base_config(
    tmp_path: Path,
    diagrams: DiagramsConfig | None,
) -> DocToolsConfig:
    return _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_diagrams=diagrams is not None,
        diagrams=diagrams,
    )


def test_generate_class_diagram_docs(tmp_path: Path) -> None:
    """Diagram generator extracts classes and inheritance."""
    src = tmp_path / "src"
    src.mkdir()

    _ = (src / "models.py").write_text(
        """
class Base:
    pass

class Child(Base):
    pass

class _Private:
    pass
""".strip(),
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "diagrams" / "classes.md"

    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
            title="Project classes",
            exclude_dirs=[],
            exclude_files=[],
            include_private=False,
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "# Project classes" in content
    assert "classDiagram" in content
    assert "class Base" in content
    assert "class Child" in content
    assert "Base <|-- Child" in content
    assert "_Private" not in content


def test_generate_class_diagram_docs_include_private(tmp_path: Path) -> None:
    """Diagram generator can include private classes."""
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "private.py").write_text("class _Private:\n    pass\n", encoding="utf-8")

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
            include_private=True,
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    assert "class _Private" in output.read_text(encoding="utf-8")


def test_generate_class_diagram_docs_skips_invalid_and_excluded(
    tmp_path: Path,
) -> None:
    """Diagram generator skips syntax errors, non-Python files and excluded paths."""
    src = tmp_path / "src"
    excluded = src / "__pycache__"
    src.mkdir()
    excluded.mkdir()

    _ = (src / "bad.py").write_text("class Broken(:\n", encoding="utf-8")
    _ = (src / "skip.txt").write_text("class NotPython:\n    pass\n", encoding="utf-8")
    _ = (src / "skip.py").write_text("class Skipped:\n    pass\n", encoding="utf-8")
    _ = (excluded / "ignored.py").write_text(
        "class Ignored:\n    pass\n",
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
            exclude_dirs=["__pycache__"],
            exclude_files=["skip.py"],
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "Ignored" not in content
    assert "NotPython" not in content
    assert "Skipped" not in content


def test_generate_class_diagram_docs_keeps_non_excluded_nested_file(
    tmp_path: Path,
) -> None:
    """Diagram generator keeps nested files when exclude rules do not match."""
    src = tmp_path / "src"
    package = src / "package"
    package.mkdir(parents=True)

    _ = (package / "models.py").write_text(
        "class NestedModel:\n    pass\n",
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
            exclude_dirs=["ignored"],
            exclude_files=["*.txt"],
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    assert "class NestedModel" in output.read_text(encoding="utf-8")


def test_generate_class_diagram_docs_missing_roots(tmp_path: Path) -> None:
    """Diagram generator ignores missing roots."""
    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[tmp_path / "missing"],
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    assert "classDiagram" in output.read_text(encoding="utf-8")


def test_generate_class_diagram_docs_multiple_roots(tmp_path: Path) -> None:
    """Diagram generator scans multiple configured roots."""
    first_src = tmp_path / "first"
    second_src = tmp_path / "second"
    first_src.mkdir()
    second_src.mkdir()

    _ = (first_src / "alpha.py").write_text(
        "class Alpha:\n    pass\n",
        encoding="utf-8",
    )
    _ = (second_src / "beta.py").write_text(
        "class Beta:\n    pass\n",
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[first_src, second_src],
            title="Multiple roots",
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "# Multiple roots" in content
    assert "class Alpha" in content
    assert "class Beta" in content


def test_generate_class_diagram_docs_handles_nested_inheritance(
    tmp_path: Path,
) -> None:
    """Diagram generator extracts inheritance chains."""
    src = tmp_path / "src"
    src.mkdir()

    _ = (src / "inheritance.py").write_text(
        """
class GrandParent:
    pass

class Parent(GrandParent):
    pass

class Child(Parent):
    pass
""".strip(),
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "class GrandParent" in content
    assert "class Parent" in content
    assert "class Child" in content
    assert "GrandParent <|-- Parent" in content
    assert "Parent <|-- Child" in content


def test_generate_class_diagram_docs_handles_empty_python_file(
    tmp_path: Path,
) -> None:
    """Diagram generator writes a valid Mermaid page even with no classes."""
    src = tmp_path / "src"
    src.mkdir()
    _ = (src / "empty.py").write_text("", encoding="utf-8")

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
            title="Empty diagram",
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "# Empty diagram" in content
    assert "classDiagram" in content


def test_generate_class_diagram_docs_handles_complex_base_expressions(
    tmp_path: Path,
) -> None:
    """Diagram generator handles attribute, subscript and unsupported base nodes."""
    src = tmp_path / "src"
    src.mkdir()

    _ = (src / "complex_bases.py").write_text(
        """
class AttributeChild(pkg.ExternalBase):
    pass

class SubscriptChild(list[int]):
    pass

class UnsupportedChild(42):
    pass
""".strip(),
        encoding="utf-8",
    )

    output = tmp_path / "docs" / "classes.md"
    cfg = _base_config(
        tmp_path,
        _make_diagrams_config(
            output_file=output,
            scan_roots=[src],
            title="Complex bases",
            include_private=True,
        ),
    )

    code = generate_class_diagram_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")

    assert "class AttributeChild" in content
    assert "class SubscriptChild" in content
    assert "class UnsupportedChild" in content

    assert "ExternalBase <|-- AttributeChild" in content
    assert "list <|-- SubscriptChild" in content
    assert "<|-- UnsupportedChild" not in content


def test_generate_class_diagram_docs_missing_config(tmp_path: Path) -> None:
    """Missing diagrams config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="diagrams"):
        _ = generate_class_diagram_docs(cfg, Console())
