# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for configuration loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools.config import load_config

if TYPE_CHECKING:
    from pathlib import Path


def test_load_config_defaults(tmp_path: Path) -> None:
    """Default configuration is valid without pyproject."""
    cfg = load_config(tmp_path)

    assert cfg.project_root == tmp_path.resolve()
    assert cfg.docs_src_dir == tmp_path.resolve() / "docs"
    assert cfg.mkdocs_config == tmp_path.resolve() / "mkdocs.yml"
    assert cfg.packages == []
    assert cfg.api is not None


def test_load_config_from_pyproject(tmp_path: Path) -> None:
    """Configuration is loaded from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    _ = pyproject.write_text(
        """
[tool.py-doc-tools]
docs_dir = "docs"
docs_src_dir = "docs/src"
mkdocs_config = "mkdocs.yml"
packages = ["magellan"]
use_emojis = true
console_emojis = false
verbose = true
enable_api = true
enable_coverage = true

[tool.py-doc-tools.api]
output_dir = "docs/src/api"
overview_enabled = true
folder_intro_enabled = true
exclude_dirs = ["__pycache__", ".git"]
exclude_files = ["__init__.py"]

[tool.py-doc-tools.coverage]
package = "magellan"
output_dir = "docs/src/coverage"
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.docs_src_dir == tmp_path.resolve() / "docs" / "src"
    assert cfg.packages == ["magellan"]
    assert cfg.use_emojis
    assert cfg.verbose
    assert cfg.enable_coverage
    assert cfg.api is not None
    assert cfg.api.overview_enabled
    assert cfg.api.folder_intro_enabled
    assert cfg.coverage is not None
    assert cfg.coverage.package == "magellan"


def test_load_config_rejects_invalid_bool(tmp_path: Path) -> None:
    """Invalid boolean values are rejected."""
    pyproject = tmp_path / "pyproject.toml"
    _ = pyproject.write_text(
        """
[tool.py-doc-tools]
use_emojis = "yes"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="use_emojis"):
        _ = load_config(tmp_path)


def test_load_config_rejects_invalid_packages(tmp_path: Path) -> None:
    """Invalid package list values are rejected."""
    pyproject = tmp_path / "pyproject.toml"
    _ = pyproject.write_text(
        """
[tool.py-doc-tools]
packages = "magellan"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="packages"):
        _ = load_config(tmp_path)
