"""Tests for coverage HTML directory configuration loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.config.loader import load_config

if TYPE_CHECKING:
    from pathlib import Path


def test_coverage_output_dir_uses_tool_coverage_html_directory(
    tmp_path: Path,
) -> None:
    """Use [tool.coverage.html].directory as coverage output fallback."""
    pyproject_toml = tmp_path / "pyproject.toml"
    _ = pyproject_toml.write_text(
        """
[tool.py-doc-tools]
enable_coverage = true

[tool.py-doc-tools.coverage]
package = "demo_package"

[tool.coverage.html]
directory = "docs/custom-coverage"
""",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.coverage is not None
    assert cfg.coverage.output_dir == tmp_path / "docs" / "custom-coverage"


def test_py_doc_tools_coverage_output_dir_has_priority(tmp_path: Path) -> None:
    """Prefer [tool.py-doc-tools.coverage].output_dir when configured."""
    pyproject_toml = tmp_path / "pyproject.toml"
    _ = pyproject_toml.write_text(
        """
[tool.py-doc-tools]
enable_coverage = true

[tool.py-doc-tools.coverage]
package = "demo_package"
output_dir = "docs/pydocs-coverage"

[tool.coverage.html]
directory = "docs/coverage-html"
""",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.coverage is not None
    assert cfg.coverage.output_dir == tmp_path / "docs" / "pydocs-coverage"


def test_coverage_html_directory_can_be_loaded_from_pixi_toml(
    tmp_path: Path,
) -> None:
    """Read coverage HTML directory from pixi.toml when available."""
    pyproject_toml = tmp_path / "pyproject.toml"
    _ = pyproject_toml.write_text(
        """
[tool.py-doc-tools]
enable_coverage = true

[tool.py-doc-tools.coverage]
package = "demo_package"
""",
        encoding="utf-8",
    )

    pixi_toml = tmp_path / "pixi.toml"
    _ = pixi_toml.write_text(
        """
[tool.coverage.html]
directory = "docs/pixi-coverage"
""",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.coverage is not None
    assert cfg.coverage.output_dir == tmp_path / "docs" / "pixi-coverage"
