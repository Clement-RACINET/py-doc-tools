"""Configuration loading public API."""

from __future__ import annotations

from py_doc_tools.config.loader import load_config
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

__all__ = [
    "ApiConfig",
    "CoverageConfig",
    "DiagnosticsConfig",
    "DiagramsConfig",
    "DocToolsConfig",
    "ExamplesConfig",
    "ReadmeConfig",
    "TagsConfig",
    "TodoConfig",
    "load_config",
]
