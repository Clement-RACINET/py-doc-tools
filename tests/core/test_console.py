"""Tests for console logging helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from py_doc_tools.core.console import Console

if TYPE_CHECKING:
    import pytest


def test_console_logs_all_levels(caplog: pytest.LogCaptureFixture) -> None:
    """Console emits log records for all public methods."""
    console = Console(verbose=True)

    with caplog.at_level(logging.DEBUG):
        console.info("info message")
        console.ok("ok message")
        console.warn("warn message")
        console.error("error message")
        console.debug("debug message")

    messages: list[str] = [record.message for record in caplog.records]

    assert "info message" in messages
    assert "ok message" in messages
    assert "warn message" in messages
    assert "error message" in messages
    assert "debug message" in messages


def test_console_configure_non_verbose() -> None:
    """Console can configure logging in non-verbose mode."""
    console = Console(verbose=False)
    console.configure()
