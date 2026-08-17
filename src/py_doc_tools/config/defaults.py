"""Default configuration values for py-doc-tools."""

from __future__ import annotations

DEFAULT_DOCS_DIR = "docs"
DEFAULT_DOCS_SRC_DIR = "docs"
DEFAULT_MKDOCS_CONFIG = "mkdocs.yml"

DEFAULT_API_OUTPUT_DIR = "docs/api"
DEFAULT_API_NAV_START_MARKER = "# --- AUTOGEN_API_START ---"
DEFAULT_API_NAV_END_MARKER = "# --- AUTOGEN_API_END ---"
DEFAULT_FOLDER_INTRO_FILENAME = "__doc__.md"

DEFAULT_COVERAGE_OUTPUT_DIR = "docs/coverage"
DEFAULT_COVERAGE_PAGE_FILE = "docs/coverage-report.md"
DEFAULT_COVERAGE_PAGE_TITLE = "Test coverage report"
DEFAULT_COVERAGE_ENTRYPOINTS = ["covindex.html", "index.html"]
DEFAULT_COVERAGE_NAV_START_MARKER = "# --- AUTOGEN_COVERAGE_START ---"
DEFAULT_COVERAGE_NAV_END_MARKER = "# --- AUTOGEN_COVERAGE_END ---"
DEFAULT_COVERAGE_NAV_ENABLED = True
DEFAULT_COVERAGE_NAV_MAX_DEPTH = 8
DEFAULT_COVERAGE_BACKLINKS_ENABLED = True
DEFAULT_COVERAGE_BACKLINK_LABEL = "← Back to documentation"

DEFAULT_EXAMPLES_SOURCE_DIR = "examples"
DEFAULT_EXAMPLES_OUTPUT_DIR = "docs/examples"
DEFAULT_EXAMPLES_ASSETS_DIR = "docs/examples/assets"
DEFAULT_EXAMPLES_NAV_START_MARKER = "# --- AUTOGEN_EXAMPLES_START ---"
DEFAULT_EXAMPLES_NAV_END_MARKER = "# --- AUTOGEN_EXAMPLES_END ---"

DEFAULT_README_SOURCE_FILE = "README.md"
DEFAULT_README_OUTPUT_FILE = "docs/readme.md"

DEFAULT_TODO_OUTPUT_FILE = "docs/todo.md"
DEFAULT_TODO_MARKERS = ["TODO", "FIXME", "BUG", "HACK", "BREAKING", "WARN"]
DEFAULT_TODO_MODE = "sections"
DEFAULT_TODO_PRESERVE_MANUAL_CONTENT = True

DEFAULT_DIAGNOSTICS_FAIL_ON_RUFF = False
DEFAULT_DIAGNOSTICS_FAIL_ON_MKDOCS = False
DEFAULT_DIAGNOSTICS_INJECT_SOURCE_TAGS = True
DEFAULT_DIAGNOSTICS_CLEAN_BEFORE_INJECT = True
DEFAULT_DIAGNOSTICS_CLEAN_LEGACY_TAGS = True
DEFAULT_DIAGNOSTICS_OUTPUT_DIR = "docs/diagnostics"

DEFAULT_TAG_DRY_RUN = False
DEFAULT_TAG_GENERATED_PREFIX = "py-doc-tools"
DEFAULT_TAG_CLEAN_LEGACY = True

DEFAULT_RUFF_OUTPUT_FILE = "docs/diagnostics/ruff.md"
DEFAULT_MKDOCS_OUTPUT_FILE = "docs/diagnostics/mkdocs.md"

DEFAULT_RUFF_TARGETS = ["src", "tests"]

DEFAULT_RUFF_EXCLUDE_DIRS = [
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    ".pixi",
    "__pycache__",
    "build",
    "dist",
    "docs/build",
    "docs/src/api",
    "docs/src/examples",
    "docs/src/diagnostics",
    "docs/src/diagrams",
]

DEFAULT_RUFF_EXCLUDE_FILES = [
    "*.pyc",
    "*.pyo",
]

DEFAULT_TAG_START_TOKEN = "# <pydocs>"
DEFAULT_TAG_END_TOKEN = "# </pydocs>"

DEFAULT_DIAGRAM_OUTPUT_FILE = "docs/diagrams/classes.md"

DEFAULT_EXCLUDE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".pixi",
    ".venv",
    "venv",
    "build",
    "dist",
]

DEFAULT_EXCLUDE_FILES = ["__init__.py"]

DEFAULT_EXAMPLES_ASSET_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
]
