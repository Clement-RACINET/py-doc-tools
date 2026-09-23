# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for README documentation generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools.config.model import DocToolsConfig, ReadmeConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError
from py_doc_tools.readme.generator import generate_readme_docs

if TYPE_CHECKING:
    from pathlib import Path


def _base_config(tmp_path: Path, readme: ReadmeConfig | None) -> DocToolsConfig:
    return DocToolsConfig(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_readme=readme is not None,
        readme=readme,
    )


def test_generate_readme_docs_with_note(tmp_path: Path) -> None:
    """README generator copies README with generated-page note."""
    source = tmp_path / "README.md"
    output = tmp_path / "docs" / "readme.md"

    _ = source.write_text("# Project\n\nHello.", encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        ReadmeConfig(
            source_file=source,
            output_file=output,
            title="Project README",
            include_toc_note=True,
        ),
    )

    code = generate_readme_docs(cfg, Console())

    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "# Project README" in content
    assert "This page is generated from the project README." in content
    assert "# Project" in content


def test_generate_readme_docs_without_note(tmp_path: Path) -> None:
    """README generator can copy raw README content."""
    source = tmp_path / "README.md"
    output = tmp_path / "docs" / "readme.md"

    _ = source.write_text("# Raw README\n", encoding="utf-8")

    cfg = _base_config(
        tmp_path,
        ReadmeConfig(
            source_file=source,
            output_file=output,
            include_toc_note=False,
        ),
    )

    code = generate_readme_docs(cfg, Console())

    assert code == 0
    assert output.read_text(encoding="utf-8") == "# Raw README\n"


def test_generate_readme_docs_missing_source(tmp_path: Path) -> None:
    """Missing README source is skipped gracefully."""
    output = tmp_path / "docs" / "readme.md"

    cfg = _base_config(
        tmp_path,
        ReadmeConfig(
            source_file=tmp_path / "MISSING.md",
            output_file=output,
        ),
    )

    code = generate_readme_docs(cfg, Console())

    assert code == 0
    assert not output.exists()


def test_generate_readme_docs_missing_config(tmp_path: Path) -> None:
    """Missing readme config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="readme"):
        _ = generate_readme_docs(cfg, Console())
