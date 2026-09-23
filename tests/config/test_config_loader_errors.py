# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Additional error-path tests for configuration loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from py_doc_tools.config import load_config
from py_doc_tools.config.exceptions import ConfigTableError, ConfigTypeError

if TYPE_CHECKING:
    from pathlib import Path


def _write_pyproject(tmp_path: Path, content: str) -> None:
    _ = (tmp_path / "pyproject.toml").write_text(
        content.strip(),
        encoding="utf-8",
    )


def test_load_config_rejects_invalid_tool_table(tmp_path: Path) -> None:
    """Invalid top-level tool table is ignored by TOML semantics test substitute."""
    _write_pyproject(
        tmp_path,
        """
tool = "invalid"
""",
    )

    cfg = load_config(tmp_path)

    assert cfg.packages == []


def test_load_config_rejects_invalid_py_doc_tools_table(tmp_path: Path) -> None:
    """Invalid py-doc-tools table raises a table error."""
    _write_pyproject(
        tmp_path,
        """
[tool]
py-doc-tools = "invalid"
""",
    )
    msg = "tool.py-doc-tools"
    with pytest.raises(ConfigTableError, match=msg):
        _ = load_config(tmp_path)


def test_load_config_rejects_invalid_api_table(tmp_path: Path) -> None:
    """Invalid API table raises a table error."""
    _write_pyproject(
        tmp_path,
        """
[tool.py-doc-tools]
api = "invalid"
""",
    )

    with pytest.raises(ConfigTableError, match="api"):
        _ = load_config(tmp_path)


def test_load_config_rejects_invalid_coverage_table(tmp_path: Path) -> None:
    """Invalid coverage table raises a table error."""
    _write_pyproject(
        tmp_path,
        """
[tool.py-doc-tools]
coverage = "invalid"
""",
    )

    with pytest.raises(ConfigTableError, match="coverage"):
        _ = load_config(tmp_path)


def test_load_config_rejects_invalid_docs_dir(tmp_path: Path) -> None:
    """Invalid string fields are rejected."""
    _write_pyproject(
        tmp_path,
        """
[tool.py-doc-tools]
docs_dir = false
""",
    )

    with pytest.raises(ConfigTypeError, match="docs_dir"):
        _ = load_config(tmp_path)


def test_load_config_rejects_invalid_optional_coverage_package(
    tmp_path: Path,
) -> None:
    """Invalid optional string fields are rejected."""
    _write_pyproject(
        tmp_path,
        """
[tool.py-doc-tools.coverage]
package = false
""",
    )

    with pytest.raises(ConfigTypeError, match="package"):
        _ = load_config(tmp_path)


def test_load_config_rejects_invalid_exclude_dirs_item(tmp_path: Path) -> None:
    """String lists reject non-string items."""
    _write_pyproject(
        tmp_path,
        """
[tool.py-doc-tools.api]
exclude_dirs = ["valid", false]
""",
    )

    with pytest.raises(ConfigTypeError, match="exclude_dirs"):
        _ = load_config(tmp_path)


def test_load_config_accepts_absolute_paths(tmp_path: Path) -> None:
    """Absolute paths are preserved by path normalization."""
    absolute_docs = tmp_path / "absolute_docs"

    _write_pyproject(
        tmp_path,
        f"""
[tool.py-doc-tools]
docs_dir = "{absolute_docs.as_posix()}"
""",
    )

    cfg = load_config(tmp_path)

    assert cfg.docs_dir == absolute_docs
