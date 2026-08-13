"""Configuration-specific exceptions."""

from __future__ import annotations


class ConfigError(Exception):
    """Base class for configuration loading errors."""


class ConfigTypeError(ConfigError, TypeError):
    """Raised when a configuration value has an invalid type."""

    def __init__(self, key: str, expected: str) -> None:
        """Initialize the exception.

        Args:
            key: Configuration key.
            expected: Expected type description.
        """
        super().__init__(f"`{key}` must be {expected}.")


class ConfigTableError(ConfigError, TypeError):
    """Raised when a TOML table has an invalid shape."""

    def __init__(self, key: str) -> None:
        """Initialize the exception.

        Args:
            key: Configuration table key.
        """
        super().__init__(f"`{key}` must be a TOML table.")
