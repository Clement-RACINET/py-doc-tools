"""Tests for the command-line interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def test_cli_generate_api(tmp_path: Path) -> None:
    """The CLI can generate API docs."""
    package_dir = tmp_path / "demo"
    package_dir.mkdir()
    _ = (package_dir / "module.py").write_text(
        "class Demo:\n    pass\n",
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    _ = (tmp_path / "mkdocs.yml").write_text(
        """
site_name: Demo
nav:
  - API:
    # --- AUTOGEN_API_START ---
    # --- AUTOGEN_API_END ---
""".lstrip(),
        encoding="utf-8",
    )

    _ = (tmp_path / "pyproject.toml").write_text(
        """
[tool.py-doc-tools]
docs_src_dir = "docs"
packages = ["demo"]

[tool.py-doc-tools.api]
output_dir = "docs/api"
exclude_files = ["__init__.py"]
""".strip(),
        encoding="utf-8",
    )

    _ = main(["--root", str(tmp_path), "generate", "--api"])

    assert (tmp_path / "docs" / "api" / "demo" / "module.md").exists()
