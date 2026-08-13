"""Additional branch tests for API generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools.api.generator import generate_api_docs
from py_doc_tools.api.nav import update_api_nav
from py_doc_tools.config.model import ApiConfig, DocToolsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from pathlib import Path


def test_generate_api_with_overview_intro_pre_post_and_emoji(tmp_path: Path) -> None:
    """API generator supports overview, intro, pre/post files and emojis."""
    package_dir = tmp_path / "demo"
    subdir = package_dir / "sub"
    subdir.mkdir(parents=True)

    _ = (package_dir / "__doc__.md").write_text(
        "Package intro.",
        encoding="utf-8",
    )
    _ = (package_dir / "client.py").write_text(
        "class Client:\n    pass\n",
        encoding="utf-8",
    )
    _ = (package_dir / "client.pre.md").write_text("Before.", encoding="utf-8")
    _ = (package_dir / "client.post.md").write_text("After.", encoding="utf-8")
    _ = (subdir / "tool.py").write_text(
        "class Tool:\n    pass\n",
        encoding="utf-8",
    )

    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        use_emojis=True,
        api=ApiConfig(
            output_dir=tmp_path / "docs" / "api",
            overview_enabled=True,
            folder_intro_enabled=True,
            exclude_files=["__init__.py"],
        ),
    )

    nav = generate_api_docs(cfg, Console())

    assert "🗺️ API overview" in nav
    assert "📂 Demo:" in nav
    assert "📖 Intro demo" in nav
    assert "📄 Client" in nav
    assert "📂 Sub:" in nav

    client_doc = tmp_path / "docs" / "api" / "demo" / "client.md"
    content = client_doc.read_text(encoding="utf-8")

    assert "Before." in content
    assert "::: demo.client" in content
    assert "After." in content


def test_generate_api_missing_package(tmp_path: Path) -> None:
    """Missing package directories are skipped."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["missing"],
        api=ApiConfig(output_dir=tmp_path / "docs" / "api"),
    )

    nav = generate_api_docs(cfg, Console())

    assert nav == ""


def test_generate_api_without_api_config(tmp_path: Path) -> None:
    """Missing API config raises a dedicated error."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        api=None,
    )

    with pytest.raises(MissingConfigSectionError, match="api"):
        _ = generate_api_docs(cfg, Console())


def test_update_api_nav_without_api_config(tmp_path: Path) -> None:
    """Missing API config raises on nav update."""
    cfg = DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        api=None,
    )

    with pytest.raises(MissingConfigSectionError, match="api"):
        update_api_nav(cfg, "")
