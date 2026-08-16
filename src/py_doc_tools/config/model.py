"""Typed configuration models for py-doc-tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003


@dataclass(frozen=True, slots=True)
class ApiConfig:
    """API documentation generation configuration."""

    output_dir: Path
    nav_start_marker: str = "# --- AUTOGEN_API_START ---"
    nav_end_marker: str = "# --- AUTOGEN_API_END ---"
    clean_output_dir: bool = True
    overview_enabled: bool = False
    folder_intro_enabled: bool = False
    folder_intro_filename: str = "__doc__.md"
    module_pre_suffix: str = ".pre.md"
    module_post_suffix: str = ".post.md"
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class CoverageConfig:
    """Coverage report generation configuration."""

    package: str | None = None
    output_dir: Path | None = None
    page_file: Path | None = None
    title: str = "Test coverage report"
    entrypoints: list[str] = field(
        default_factory=lambda: ["covindex.html", "index.html"],
    )
    branch: bool = True
    quiet: bool = True

    nav_enabled: bool = True
    nav_start_marker: str = "# --- AUTOGEN_COVERAGE_START ---"
    nav_end_marker: str = "# --- AUTOGEN_COVERAGE_END ---"
    nav_max_depth: int = 8

    inject_backlinks: bool = True
    backlink_label: str = "← Back to documentation"

@dataclass(frozen=True, slots=True)
class ExamplesConfig:
    """Examples documentation generation configuration."""

    source_dir: Path
    output_dir: Path
    assets_dir: Path
    nav_start_marker: str = "# --- AUTOGEN_EXAMPLES_START ---"
    nav_end_marker: str = "# --- AUTOGEN_EXAMPLES_END ---"
    overview_enabled: bool = True
    copy_assets: bool = True
    show_image_previews: bool = True
    preview_max_width_px: int = 420
    skip_dirs: list[str] = field(default_factory=list)
    skip_files: list[str] = field(default_factory=list)
    asset_extensions: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReadmeConfig:
    """README documentation mirroring configuration."""

    source_file: Path
    output_file: Path
    title: str = "README"
    include_toc_note: bool = True


@dataclass(frozen=True, slots=True)
class TodoConfig:
    """TODO/FIXME documentation generation configuration."""

    output_file: Path
    scan_roots: list[Path] = field(default_factory=list)
    markers: list[str] = field(
        default_factory=lambda: ["TODO", "FIXME", "BUG", "HACK"],
    )
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DiagnosticsConfig:
    """Diagnostics documentation generation configuration."""

    output_dir: Path
    ruff_output_file: Path
    mkdocs_output_file: Path
    enable_ruff: bool = True
    enable_mkdocs: bool = True
    mkdocs_strict: bool = False


@dataclass(frozen=True, slots=True)
class TagsConfig:
    """Optional source tag injection configuration."""

    scan_roots: list[Path] = field(default_factory=list)
    dry_run: bool = True
    start_token: str = "# <pydocs>"
    end_token: str = "# </pydocs>"
    markers: list[str] = field(
        default_factory=lambda: ["TODO", "FIXME", "BUG", "HACK"],
    )
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DiagramsConfig:
    """Class diagram documentation generation configuration."""

    output_file: Path
    scan_roots: list[Path] = field(default_factory=list)
    title: str = "Class diagram"
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)
    include_private: bool = False


@dataclass(frozen=True, slots=True)
class DocToolsConfig:
    """Root py-doc-tools configuration."""

    project_root: Path
    docs_dir: Path
    docs_src_dir: Path
    mkdocs_config: Path
    packages: list[str] = field(default_factory=list)

    use_emojis: bool = False
    console_emojis: bool = False
    verbose: bool = False

    enable_api: bool = False
    enable_coverage: bool = False
    enable_examples: bool = False
    enable_readme: bool = False
    enable_todo: bool = False
    enable_diagnostics: bool = False
    enable_tags: bool = False
    enable_diagrams: bool = False

    api: ApiConfig | None = None
    coverage: CoverageConfig | None = None
    examples: ExamplesConfig | None = None
    readme: ReadmeConfig | None = None
    todo: TodoConfig | None = None
    diagnostics: DiagnosticsConfig | None = None
    tags: TagsConfig | None = None
    diagrams: DiagramsConfig | None = None
