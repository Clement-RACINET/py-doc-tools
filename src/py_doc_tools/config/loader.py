# SPDX-FileCopyrightText: 2026 C. RACINET
#
# SPDX-License-Identifier: X11

"""Configuration loading from pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast

from py_doc_tools.config.defaults import (
    DEFAULT_API_NAV_END_MARKER,
    DEFAULT_API_NAV_START_MARKER,
    DEFAULT_API_OUTPUT_DIR,
    DEFAULT_COVERAGE_BACKLINK_LABEL,
    DEFAULT_COVERAGE_BACKLINKS_ENABLED,
    DEFAULT_COVERAGE_ENTRYPOINTS,
    DEFAULT_COVERAGE_NAV_ENABLED,
    DEFAULT_COVERAGE_NAV_END_MARKER,
    DEFAULT_COVERAGE_NAV_MAX_DEPTH,
    DEFAULT_COVERAGE_NAV_START_MARKER,
    DEFAULT_COVERAGE_OUTPUT_DIR,
    DEFAULT_COVERAGE_PAGE_FILE,
    DEFAULT_COVERAGE_PAGE_TITLE,
    DEFAULT_DIAGNOSTICS_CLEAN_BEFORE_INJECT,
    DEFAULT_DIAGNOSTICS_CLEAN_LEGACY_TAGS,
    DEFAULT_DIAGNOSTICS_FAIL_ON_MKDOCS,
    DEFAULT_DIAGNOSTICS_FAIL_ON_RUFF,
    DEFAULT_DIAGNOSTICS_INJECT_SOURCE_TAGS,
    DEFAULT_DIAGNOSTICS_OUTPUT_DIR,
    DEFAULT_DIAGRAM_OUTPUT_FILE,
    DEFAULT_DOCS_DIR,
    DEFAULT_DOCS_SRC_DIR,
    DEFAULT_EXAMPLES_ASSET_EXTENSIONS,
    DEFAULT_EXAMPLES_ASSETS_DIR,
    DEFAULT_EXAMPLES_NAV_END_MARKER,
    DEFAULT_EXAMPLES_NAV_START_MARKER,
    DEFAULT_EXAMPLES_OUTPUT_DIR,
    DEFAULT_EXAMPLES_SOURCE_DIR,
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_FILES,
    DEFAULT_FOLDER_INTRO_FILENAME,
    DEFAULT_MKDOCS_CONFIG,
    DEFAULT_MKDOCS_OUTPUT_FILE,
    DEFAULT_README_OUTPUT_FILE,
    DEFAULT_README_SOURCE_FILE,
    DEFAULT_RUFF_EXCLUDE_DIRS,
    DEFAULT_RUFF_EXCLUDE_FILES,
    DEFAULT_RUFF_OUTPUT_FILE,
    DEFAULT_RUFF_TARGETS,
    DEFAULT_TAG_CLEAN_LEGACY,
    DEFAULT_TAG_DRY_RUN,
    DEFAULT_TAG_END_TOKEN,
    DEFAULT_TAG_GENERATED_PREFIX,
    DEFAULT_TAG_START_TOKEN,
    DEFAULT_TODO_MARKERS,
    DEFAULT_TODO_MODE,
    DEFAULT_TODO_OUTPUT_FILE,
    DEFAULT_TODO_PRESERVE_MANUAL_CONTENT,
)
from py_doc_tools.config.exceptions import ConfigTableError, ConfigTypeError
from py_doc_tools.config.model import (
    ApiConfig,
    CoverageConfig,
    DiagnosticsConfig,
    DiagramsConfig,
    DocToolsConfig,
    ExamplesConfig,
    ReadmeConfig,
    TagsConfig,
    TodoConfig,
)

TomlTable = dict[str, object]


def load_config(project_root: Path | None = None) -> DocToolsConfig:
    """Load py-doc-tools configuration from project TOML files."""
    root = Path.cwd() if project_root is None else project_root
    resolved_root = root.resolve()

    tool_table = _load_merged_tool_table(resolved_root)

    config_raw = _table_value(tool_table, "py-doc-tools", {})
    config_table = _as_table(config_raw, "tool.py-doc-tools")

    return _build_config(resolved_root, config_table, tool_table)


def _build_config(
    root: Path,
    table: TomlTable,
    tool_table: TomlTable | None = None,
) -> DocToolsConfig:
    full_tool_table = {} if tool_table is None else tool_table
    api_table = _subtable(table, "api")
    coverage_table = _subtable(table, "coverage")
    examples_table = _subtable(table, "examples")
    readme_table = _subtable(table, "readme")
    todo_table = _subtable(table, "todo")
    diagnostics_table = _subtable(table, "diagnostics")
    tags_table = _subtable(table, "tags")
    diagrams_table = _subtable(table, "diagrams")

    has_api_table = "api" in table
    has_coverage_table = "coverage" in table
    has_examples_table = "examples" in table
    has_readme_table = "readme" in table
    has_todo_table = "todo" in table
    has_diagnostics_table = "diagnostics" in table
    has_tags_table = "tags" in table
    has_diagrams_table = "diagrams" in table

    enable_api = _bool(table, "enable_api", default=has_api_table or not table)
    enable_coverage = _bool(table, "enable_coverage", default=has_coverage_table)
    enable_examples = _bool(table, "enable_examples", default=False)
    enable_readme = _bool(table, "enable_readme", default=False)
    enable_todo = _bool(table, "enable_todo", default=False)
    enable_diagnostics = _bool(table, "enable_diagnostics", default=False)
    enable_tags = _bool(table, "enable_tags", default=False)
    enable_diagrams = _bool(table, "enable_diagrams", default=False)

    api_config = (
        _build_api_config(root, api_table)
        if enable_api or has_api_table or not table
        else None
    )
    coverage_config = (
        _build_coverage_config(root, coverage_table, full_tool_table)
        if enable_coverage or has_coverage_table
        else None
    )
    examples_config = (
        _build_examples_config(root, examples_table)
        if enable_examples or has_examples_table
        else None
    )
    readme_config = (
        _build_readme_config(root, readme_table)
        if enable_readme or has_readme_table
        else None
    )
    todo_config = (
        _build_todo_config(root, todo_table) if enable_todo or has_todo_table else None
    )
    diagnostics_config = (
        _build_diagnostics_config(root, diagnostics_table)
        if enable_diagnostics or has_diagnostics_table
        else None
    )
    tags_config = (
        _build_tags_config(root, tags_table) if enable_tags or has_tags_table else None
    )
    diagrams_config = (
        _build_diagrams_config(root, diagrams_table)
        if enable_diagrams or has_diagrams_table
        else None
    )

    return DocToolsConfig(
        root,
        _path(root, _string(table, "docs_dir", DEFAULT_DOCS_DIR)),
        _path(
            root,
            _string(table, "docs_src_dir", DEFAULT_DOCS_SRC_DIR),
        ),
        _path(
            root,
            _string(table, "mkdocs_config", DEFAULT_MKDOCS_CONFIG),
        ),
        _string_list(table, "packages", []),
        _bool(table, "use_emojis", default=False),
        _bool(table, "console_emojis", default=False),
        _bool(table, "verbose", default=False),
        enable_api,
        enable_coverage,
        enable_examples,
        enable_readme,
        enable_todo,
        enable_diagnostics,
        enable_tags,
        enable_diagrams,
        api_config,
        coverage_config,
        examples_config,
        readme_config,
        todo_config,
        diagnostics_config,
        tags_config,
        diagrams_config,
    )


def _build_api_config(root: Path, table: TomlTable) -> ApiConfig:
    return ApiConfig(
        output_dir=_path(root, _string(table, "output_dir", DEFAULT_API_OUTPUT_DIR)),
        nav_start_marker=_string(
            table,
            "nav_start_marker",
            DEFAULT_API_NAV_START_MARKER,
        ),
        nav_end_marker=_string(
            table,
            "nav_end_marker",
            DEFAULT_API_NAV_END_MARKER,
        ),
        clean_output_dir=_bool(table, "clean_output_dir", default=True),
        overview_enabled=_bool(table, "overview_enabled", default=False),
        folder_intro_enabled=_bool(
            table,
            "folder_intro_enabled",
            default=False,
        ),
        folder_intro_filename=_string(
            table,
            "folder_intro_filename",
            DEFAULT_FOLDER_INTRO_FILENAME,
        ),
        module_pre_suffix=_string(table, "module_pre_suffix", ".pre.md"),
        module_post_suffix=_string(table, "module_post_suffix", ".post.md"),
        exclude_dirs=_string_list(table, "exclude_dirs", DEFAULT_EXCLUDE_DIRS),
        exclude_files=_string_list(table, "exclude_files", DEFAULT_EXCLUDE_FILES),
    )


def _build_coverage_config(
    root: Path,
    table: TomlTable,
    tool_table: TomlTable,
) -> CoverageConfig:
    output_dir = _string(
        table,
        "output_dir",
        _coverage_html_directory(tool_table) or DEFAULT_COVERAGE_OUTPUT_DIR,
    )

    return CoverageConfig(
        package=_optional_string(table, "package", None),
        output_dir=_path(root, output_dir),
        page_file=_path(
            root,
            _string(table, "page_file", DEFAULT_COVERAGE_PAGE_FILE),
        ),
        title=_string(table, "title", DEFAULT_COVERAGE_PAGE_TITLE),
        entrypoints=_string_list(
            table,
            "entrypoints",
            DEFAULT_COVERAGE_ENTRYPOINTS,
        ),
        branch=_bool(table, "branch", default=True),
        quiet=_bool(table, "quiet", default=True),
        nav_enabled=_bool(
            table,
            "nav_enabled",
            default=DEFAULT_COVERAGE_NAV_ENABLED,
        ),
        nav_start_marker=_string(
            table,
            "nav_start_marker",
            DEFAULT_COVERAGE_NAV_START_MARKER,
        ),
        nav_end_marker=_string(
            table,
            "nav_end_marker",
            DEFAULT_COVERAGE_NAV_END_MARKER,
        ),
        nav_max_depth=_int(
            table,
            "nav_max_depth",
            DEFAULT_COVERAGE_NAV_MAX_DEPTH,
        ),
        inject_backlinks=_bool(
            table,
            "inject_backlinks",
            default=DEFAULT_COVERAGE_BACKLINKS_ENABLED,
        ),
        backlink_label=_string(
            table,
            "backlink_label",
            DEFAULT_COVERAGE_BACKLINK_LABEL,
        ),
    )


def _build_examples_config(root: Path, table: TomlTable) -> ExamplesConfig:
    return ExamplesConfig(
        source_dir=_path(
            root,
            _string(table, "source_dir", DEFAULT_EXAMPLES_SOURCE_DIR),
        ),
        output_dir=_path(
            root,
            _string(table, "output_dir", DEFAULT_EXAMPLES_OUTPUT_DIR),
        ),
        assets_dir=_path(
            root,
            _string(table, "assets_dir", DEFAULT_EXAMPLES_ASSETS_DIR),
        ),
        mode=_string(table, "mode", "directory"),
        nav_start_marker=_string(
            table,
            "nav_start_marker",
            DEFAULT_EXAMPLES_NAV_START_MARKER,
        ),
        nav_end_marker=_string(
            table,
            "nav_end_marker",
            DEFAULT_EXAMPLES_NAV_END_MARKER,
        ),
        overview_enabled=_bool(table, "overview_enabled", default=True),
        copy_assets=_bool(table, "copy_assets", default=True),
        show_image_previews=_bool(
            table,
            "show_image_previews",
            default=True,
        ),
        preview_max_width_px=_int(table, "preview_max_width_px", 420),
        clean_output_dir=_bool(table, "clean_output_dir", default=True),
        skip_dirs=_string_list(table, "skip_dirs", DEFAULT_EXCLUDE_DIRS),
        skip_files=_string_list(table, "skip_files", DEFAULT_EXCLUDE_FILES),
        asset_extensions=_string_list(
            table,
            "asset_extensions",
            DEFAULT_EXAMPLES_ASSET_EXTENSIONS,
        ),
        folder_doc_filename=_string(table, "folder_doc_filename", "__doc__.md"),
        input_dir_suffix=_string(table, "input_dir_suffix", ".inputs"),
        output_dir_suffix=_string(table, "output_dir_suffix", ".outputs"),
    )


def _build_readme_config(root: Path, table: TomlTable) -> ReadmeConfig:
    return ReadmeConfig(
        source_file=_path(
            root,
            _string(table, "source_file", DEFAULT_README_SOURCE_FILE),
        ),
        output_file=_path(
            root,
            _string(table, "output_file", DEFAULT_README_OUTPUT_FILE),
        ),
        title=_string(table, "title", "README"),
        include_toc_note=_bool(table, "include_toc_note", default=True),
    )


def _build_todo_config(root: Path, table: TomlTable) -> TodoConfig:
    scan_roots = [
        _path(root, value) for value in _string_list(table, "scan_roots", ["src"])
    ]

    return TodoConfig(
        output_file=_path(
            root,
            _string(table, "output_file", DEFAULT_TODO_OUTPUT_FILE),
        ),
        scan_roots=scan_roots,
        markers=_string_list(table, "markers", DEFAULT_TODO_MARKERS),
        exclude_dirs=_string_list(table, "exclude_dirs", DEFAULT_EXCLUDE_DIRS),
        exclude_files=_string_list(table, "exclude_files", []),
        mode=_string(table, "mode", DEFAULT_TODO_MODE),
        preserve_manual_content=_bool(
            table,
            "preserve_manual_content",
            default=DEFAULT_TODO_PRESERVE_MANUAL_CONTENT,
        ),
    )


def _build_diagnostics_config(root: Path, table: TomlTable) -> DiagnosticsConfig:
    return DiagnosticsConfig(
        output_dir=_path(
            root,
            _string(table, "output_dir", DEFAULT_DIAGNOSTICS_OUTPUT_DIR),
        ),
        ruff_output_file=_path(
            root,
            _string(table, "ruff_output_file", DEFAULT_RUFF_OUTPUT_FILE),
        ),
        mkdocs_output_file=_path(
            root,
            _string(table, "mkdocs_output_file", DEFAULT_MKDOCS_OUTPUT_FILE),
        ),
        enable_ruff=_bool(table, "enable_ruff", default=True),
        enable_mkdocs=_bool(table, "enable_mkdocs", default=True),
        mkdocs_strict=_bool(table, "mkdocs_strict", default=False),
        fail_on_ruff=_bool(
            table,
            "fail_on_ruff",
            default=DEFAULT_DIAGNOSTICS_FAIL_ON_RUFF,
        ),
        fail_on_mkdocs=_bool(
            table,
            "fail_on_mkdocs",
            default=DEFAULT_DIAGNOSTICS_FAIL_ON_MKDOCS,
        ),
        inject_source_tags=_bool(
            table,
            "inject_source_tags",
            default=DEFAULT_DIAGNOSTICS_INJECT_SOURCE_TAGS,
        ),
        clean_before_inject=_bool(
            table,
            "clean_before_inject",
            default=DEFAULT_DIAGNOSTICS_CLEAN_BEFORE_INJECT,
        ),
        clean_legacy_tags=_bool(
            table,
            "clean_legacy_tags",
            default=DEFAULT_DIAGNOSTICS_CLEAN_LEGACY_TAGS,
        ),
        ruff_targets=_string_list(
            table,
            "ruff_targets",
            DEFAULT_RUFF_TARGETS,
        ),
        ruff_exclude_dirs=_string_list(
            table,
            "ruff_exclude_dirs",
            DEFAULT_RUFF_EXCLUDE_DIRS,
        ),
        ruff_exclude_files=_string_list(
            table,
            "ruff_exclude_files",
            DEFAULT_RUFF_EXCLUDE_FILES,
        ),
    )


def _build_tags_config(root: Path, table: TomlTable) -> TagsConfig:
    scan_roots = [
        _path(root, value) for value in _string_list(table, "scan_roots", ["src"])
    ]

    return TagsConfig(
        scan_roots=scan_roots,
        dry_run=_bool(table, "dry_run", default=DEFAULT_TAG_DRY_RUN),
        generated_prefix=_string(
            table,
            "generated_prefix",
            DEFAULT_TAG_GENERATED_PREFIX,
        ),
        clean_legacy=_bool(
            table,
            "clean_legacy",
            default=DEFAULT_TAG_CLEAN_LEGACY,
        ),
        start_token=_string(table, "start_token", DEFAULT_TAG_START_TOKEN),
        end_token=_string(table, "end_token", DEFAULT_TAG_END_TOKEN),
        markers=_string_list(table, "markers", DEFAULT_TODO_MARKERS),
        exclude_dirs=_string_list(table, "exclude_dirs", DEFAULT_EXCLUDE_DIRS),
        exclude_files=_string_list(table, "exclude_files", []),
    )


def _build_diagrams_config(root: Path, table: TomlTable) -> DiagramsConfig:
    scan_roots = [
        _path(root, value) for value in _string_list(table, "scan_roots", ["src"])
    ]

    return DiagramsConfig(
        output_file=_path(
            root,
            _string(table, "output_file", DEFAULT_DIAGRAM_OUTPUT_FILE),
        ),
        scan_roots=scan_roots,
        title=_string(table, "title", "Class diagram"),
        exclude_dirs=_string_list(table, "exclude_dirs", DEFAULT_EXCLUDE_DIRS),
        exclude_files=_string_list(table, "exclude_files", []),
        include_private=_bool(table, "include_private", default=False),
    )


def _load_merged_tool_table(root: Path) -> TomlTable:
    """Load and merge [tool] tables from pyproject.toml and pixi.toml."""
    merged: TomlTable = {}

    for filename in ("pyproject.toml", "pixi.toml"):
        path = root / filename
        if not path.exists():
            continue

        with path.open("rb") as file:
            loaded = cast("dict[object, object]", tomllib.load(file))

        raw = _as_table(loaded, filename)
        tool = _table_value(raw, "tool", {})

        if not isinstance(tool, dict):
            continue

        typed_tool = cast("dict[object, object]", tool)
        tool_table = _as_table(typed_tool, f"{filename}.tool")
        _deep_update(merged, tool_table)

    return merged


def _deep_update(target: TomlTable, source: TomlTable) -> None:
    """Recursively merge source into target."""
    for key, value in source.items():
        current = target.get(key)

        if isinstance(current, dict) and isinstance(value, dict):
            current_table = cast("TomlTable", current)
            value_table = cast("TomlTable", value)
            _deep_update(current_table, value_table)
            target[key] = current_table
            continue

        target[key] = value


def _coverage_html_directory(tool_table: TomlTable) -> str | None:
    """Read [tool.coverage.html].directory from the merged tool table."""
    coverage_raw = _table_value(tool_table, "coverage", {})
    coverage_table = _as_table(coverage_raw, "tool.coverage")

    html_raw = _table_value(coverage_table, "html", {})
    html_table = _as_table(html_raw, "tool.coverage.html")

    directory = _table_value(html_table, "directory", None)

    if directory is None:
        return None

    if not isinstance(directory, str):
        msg = "tool.coverage.html.directory"
        raise ConfigTypeError(msg, "a string")

    return directory


def _subtable(table: TomlTable, key: str) -> TomlTable:
    value = _table_value(table, key, {})
    return _as_table(value, key)


def _table_value(table: TomlTable, key: str, default: object) -> object:
    return table.get(key, default)


def _as_table(value: object, name: str) -> TomlTable:
    if not isinstance(value, dict):
        raise ConfigTableError(name)

    object_dict = cast("dict[object, object]", value)
    result: TomlTable = {}

    for key, item in object_dict.items():
        if not isinstance(key, str):
            raise ConfigTypeError(name, "a TOML table with string keys")
        result[key] = item

    return result


def _string(table: TomlTable, key: str, default: str) -> str:
    value = _table_value(table, key, default)
    if not isinstance(value, str):
        raise ConfigTypeError(key, "a string")
    return value


def _optional_string(
    table: TomlTable,
    key: str,
    default: str | None,
) -> str | None:
    value = _table_value(table, key, default)
    if value is None:
        return None

    if not isinstance(value, str):
        raise ConfigTypeError(key, "a string or null")

    return value


def _bool(table: TomlTable, key: str, *, default: bool) -> bool:
    value = _table_value(table, key, default)
    if not isinstance(value, bool):
        raise ConfigTypeError(key, "a boolean")
    return value


def _int(table: TomlTable, key: str, default: int) -> int:
    value = _table_value(table, key, default)
    if not isinstance(value, int):
        raise ConfigTypeError(key, "an integer")
    return value


def _string_list(
    table: TomlTable,
    key: str,
    default: list[str],
) -> list[str]:
    value = _table_value(table, key, default)
    if not isinstance(value, list):
        raise ConfigTypeError(key, "a list of strings")

    object_list = cast("list[object]", value)
    result: list[str] = []

    for item in object_list:
        if not isinstance(item, str):
            raise ConfigTypeError(key, "a list of strings")
        result.append(item)

    return result


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path
