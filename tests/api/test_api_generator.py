# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Tests for API generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.api import generate_api_docs, update_api_nav
from py_doc_tools.config import load_config
from py_doc_tools.core.console import Console

if TYPE_CHECKING:
    from pathlib import Path


def test_generate_api_docs_and_update_nav(tmp_path: Path) -> None:
    """API docs are generated and injected into mkdocs.yml."""
    package_dir = tmp_path / "demo"
    package_dir.mkdir()
    _ = (package_dir / "__init__.py").write_text("", encoding="utf-8")
    _ = (package_dir / "client.py").write_text(
        "class Client:\n    pass\n",
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    mkdocs = tmp_path / "mkdocs.yml"
    _ = mkdocs.write_text(
        """
site_name: Demo
nav:
  - API:
    # --- AUTOGEN_API_START ---
    # --- AUTOGEN_API_END ---
""".lstrip(),
        encoding="utf-8",
    )

    pyproject = tmp_path / "pyproject.toml"
    _ = pyproject.write_text(
        """
[tool.py-doc-tools]
docs_src_dir = "docs"
mkdocs_config = "mkdocs.yml"
packages = ["demo"]
use_emojis = false

[tool.py-doc-tools.api]
output_dir = "docs/api"
exclude_files = ["__init__.py"]
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    console = Console(verbose=True)
    console.configure()

    nav = generate_api_docs(cfg, console)
    update_api_nav(cfg, nav)

    generated = tmp_path / "docs" / "api" / "demo" / "client.md"
    assert generated.exists()
    assert "::: demo.client" in generated.read_text(encoding="utf-8")

    content = mkdocs.read_text(encoding="utf-8")
    assert "Client: api/demo/client.md" in content
