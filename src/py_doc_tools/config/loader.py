"""Load py-doc-tools configuration from ``pyproject.toml``."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from py_doc_tools.config.defaults import (
    DEFAULT_API_END_MARKER,
    DEFAULT_API_EXCLUDE_DIRS,
    DEFAULT_API_EXCLUDE_FILES,
    DEFAULT_API_START_MARKER,
)
from py_doc_tools.config.exceptions import ConfigTableError, ConfigTypeError
from py_doc_tools.config.model import ApiConfig, CoverageConfig, DocToolsConfig

type TomlValue = str | bool | int | float | list[object] | dict[str, object] | None
type TomlTable = dict[str, TomlValue]


def load_config(project_root: Path | str = ".") -> DocToolsConfig:
    """Load the documentation tool configuration.

    Args:
        project_root: Project root directory.

    Returns:
        Fully resolved configuration.
    """
    root = Path(project_root).resolve()
    pyproject = root / "pyproject.toml"

    data: TomlTable = {}

    if pyproject.exists():
        with pyproject.open("rb") as stream:
            raw = cast("dict[str, object]", tomllib.load(stream))
        data = _read_tool_config(raw)

    docs_dir = _path(root, _get_str(data, "docs_dir", "docs"))
    docs_src_dir = _path(root, _get_str(data, "docs_src_dir", "docs"))
    mkdocs_config = _path(root, _get_str(data, "mkdocs_config", "mkdocs.yml"))

    api_table = _get_table(data, "api")
    coverage_table = _get_table(data, "coverage")

    return DocToolsConfig(
        project_root=root,
        docs_dir=docs_dir,
        docs_src_dir=docs_src_dir,
        mkdocs_config=mkdocs_config,
        packages=_get_str_list(data, "packages", []),
        use_emojis=_get_bool(data, "use_emojis", default=False),
        console_emojis=_get_bool(data, "console_emojis", default=False),
        verbose=_get_bool(data, "verbose", default=False),
        enable_api=_get_bool(data, "enable_api", default=True),
        enable_coverage=_get_bool(data, "enable_coverage", default=False),
        api=_build_api_config(root, docs_src_dir, api_table),
        coverage=_build_coverage_config(root, coverage_table),
    )


def _read_tool_config(raw: dict[str, object]) -> TomlTable:
    tool = raw.get("tool")
    if not isinstance(tool, dict):
        return {}

    tool_table = cast("dict[str, object]", tool)
    config = tool_table.get("py-doc-tools")

    if config is None:
        return {}

    if not isinstance(config, dict):
        msg = "tool.py-doc-tools"
        raise ConfigTableError(msg)

    return cast("TomlTable", config)


def _build_api_config(
    root: Path,
    docs_src_dir: Path,
    table: TomlTable,
) -> ApiConfig:
    output_default = docs_src_dir / "api"
    output_dir = _path(root, _get_str(table, "output_dir", output_default.as_posix()))

    return ApiConfig(
        output_dir=output_dir,
        nav_start_marker=_get_str(
            table,
            "nav_start_marker",
            DEFAULT_API_START_MARKER,
        ),
        nav_end_marker=_get_str(
            table,
            "nav_end_marker",
            DEFAULT_API_END_MARKER,
        ),
        clean_output_dir=_get_bool(table, "clean_output_dir", default=True),
        overview_enabled=_get_bool(table, "overview_enabled", default=False),
        folder_intro_enabled=_get_bool(table, "folder_intro_enabled", default=False),
        folder_intro_filename=_get_str(table, "folder_intro_filename", "__doc__.md"),
        module_pre_suffix=_get_str(table, "module_pre_suffix", ".pre.md"),
        module_post_suffix=_get_str(table, "module_post_suffix", ".post.md"),
        exclude_dirs=set(
            _get_str_list(
                table,
                "exclude_dirs",
                sorted(DEFAULT_API_EXCLUDE_DIRS),
            ),
        ),
        exclude_files=_get_str_list(
            table,
            "exclude_files",
            list(DEFAULT_API_EXCLUDE_FILES),
        ),
    )


def _build_coverage_config(root: Path, table: TomlTable) -> CoverageConfig:
    output_dir = _path(root, _get_str(table, "output_dir", "docs/coverage"))

    return CoverageConfig(
        package=_get_optional_str(table, "package"),
        output_dir=output_dir,
        branch=_get_bool(table, "branch", default=True),
        quiet=_get_bool(table, "quiet", default=True),
    )


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def _get_table(data: TomlTable, key: str) -> TomlTable:
    value = data.get(key)

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ConfigTableError(key)

    return cast("TomlTable", value)


def _get_str(data: TomlTable, key: str, default: str) -> str:
    value = data.get(key, default)

    if not isinstance(value, str):
        raise ConfigTypeError(key, "a string")

    return value


def _get_optional_str(data: TomlTable, key: str) -> str | None:
    value = data.get(key)

    if value is None:
        return None

    if not isinstance(value, str):
        raise ConfigTypeError(key, "a string")

    return value


def _get_bool(data: TomlTable, key: str, *, default: bool) -> bool:
    value = data.get(key, default)

    if not isinstance(value, bool):
        raise ConfigTypeError(key, "a boolean")

    return value


def _get_str_list(data: TomlTable, key: str, default: list[str]) -> list[str]:
    value = data.get(key, default)

    if not isinstance(value, list):
        raise ConfigTypeError(key, "a list of strings")

    result: list[str] = []

    for item in value:
        if not isinstance(item, str):
            raise ConfigTypeError(key, "a list of strings")
        result.append(item)

    return result
