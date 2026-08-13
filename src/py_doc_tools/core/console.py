"""Console logging helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Console:
    """Small wrapper around logging for consistent CLI output."""

    verbose: bool = False

    def configure(self) -> None:
        """Configure root logging for CLI execution."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

    def info(self, message: str) -> None:
        """Log an informational message."""
        logging.info(message)

    def ok(self, message: str) -> None:
        """Log a success message."""
        logging.info(message)

    def warn(self, message: str) -> None:
        """Log a warning message."""
        logging.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        logging.error(message)

    def debug(self, message: str) -> None:
        """Log a debug message."""
        logging.debug(message)
