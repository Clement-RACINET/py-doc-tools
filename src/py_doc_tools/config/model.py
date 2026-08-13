"""Typed configuration models for py-doc-tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from py_doc_tools.config.defaults import (
    DEFAULT_API_END_MARKER,
    DEFAULT_API_EXCLUDE_DIRS,
    DEFAULT_API_EXCLUDE_FILES,
    DEFAULT_API_START_MARKER,
)


@dataclass(frozen=True, slots=True)
class ApiConfig:
    """Configuration for API documentation generation."""

    output_dir: Path
    nav_start_marker: str = DEFAULT_API_START_MARKER
    nav_end_marker: str = DEFAULT_API_END_MARKER
    clean_output_dir: bool = True
    overview_enabled: bool = False
    folder_intro_enabled: bool = False
    folder_intro_filename: str = "__doc__.md"
    module_pre_suffix: str = ".pre.md"
    module_post_suffix: str = ".post.md"
    exclude_dirs: set[str] = field(
        default_factory=lambda: set(DEFAULT_API_EXCLUDE_DIRS),
    )
    exclude_files: list[str] = field(
        default_factory=lambda: list(DEFAULT_API_EXCLUDE_FILES),
    )


@dataclass(frozen=True, slots=True)
class CoverageConfig:
    """Configuration for pytest coverage report generation."""

    package: str | None = None
    output_dir: Path = Path("docs/coverage")
    branch: bool = True
    quiet: bool = True


@dataclass(frozen=True, slots=True)
class DocToolsConfig:
    """Root configuration for the documentation toolchain."""

    project_root: Path
    docs_dir: Path
    docs_src_dir: Path
    mkdocs_config: Path
    packages: list[str]
    use_emojis: bool = False
    console_emojis: bool = False
    verbose: bool = False
    enable_api: bool = True
    enable_coverage: bool = False
    api: ApiConfig | None = None
    coverage: CoverageConfig | None = None
