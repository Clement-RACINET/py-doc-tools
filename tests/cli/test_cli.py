"""Tests for the command-line interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from py_doc_tools.cli import main

if TYPE_CHECKING:
    from pathlib import Path

SUCCESS_CODE = 0


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


def test_cli_tags_clean_write(tmp_path: Path) -> None:
    """The CLI can remove generated source tags."""
    src = tmp_path / "src"
    src.mkdir()

    module = src / "module.py"
    _ = module.write_text(
        "\n".join(
            [
                "# FIXME[py-doc-tools:Ruff:T201]: generated",
                "# TODO: keep human note",
                "value = 'hello'",
                "",
            ],
        ),
        encoding="utf-8",
    )

    _ = (tmp_path / "pyproject.toml").write_text(
        """
[tool.py-doc-tools]
enable_tags = true

[tool.py-doc-tools.tags]
scan_roots = ["src"]
dry_run = true
generated_prefix = "py-doc-tools"
exclude_dirs = []
exclude_files = []
""".strip(),
        encoding="utf-8",
    )

    code = main(["--root", str(tmp_path), "tags", "clean", "--write"])

    content = module.read_text(encoding="utf-8")

    assert code == SUCCESS_CODE
    assert "py-doc-tools:Ruff:T201" not in content
    assert "# TODO: keep human note" in content
    assert "value = 'hello'" in content


def test_cli_tags_clean_default_is_dry_run(tmp_path: Path) -> None:
    """The CLI does not write files by default for tags clean."""
    src = tmp_path / "src"
    src.mkdir()

    module = src / "module.py"
    original = "\n".join(
        [
            "# FIXME[py-doc-tools:Ruff:T201]: generated",
            "value = 'hello'",
            "",
        ],
    )
    _ = module.write_text(original, encoding="utf-8")

    _ = (tmp_path / "pyproject.toml").write_text(
        """
[tool.py-doc-tools]
enable_tags = true

[tool.py-doc-tools.tags]
scan_roots = ["src"]
dry_run = false
generated_prefix = "py-doc-tools"
exclude_dirs = []
exclude_files = []
""".strip(),
        encoding="utf-8",
    )

    code = main(["--root", str(tmp_path), "tags", "clean"])

    assert code == SUCCESS_CODE
    assert module.read_text(encoding="utf-8") == original
