"""Default configuration values for py-doc-tools."""

from __future__ import annotations

DEFAULT_API_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".git",
        ".hg",
        ".svn",
        ".pixi",
        ".venv",
        "venv",
        "build",
        "dist",
    },
)

DEFAULT_API_EXCLUDE_FILES: tuple[str, ...] = (
    "__init__.py",
    "test_*.py",
)

DEFAULT_API_START_MARKER = "# --- AUTOGEN_API_START ---"
DEFAULT_API_END_MARKER = "# --- AUTOGEN_API_END ---"
