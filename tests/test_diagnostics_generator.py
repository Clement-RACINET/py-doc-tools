"""Tests for diagnostics documentation generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

import py_doc_tools.diagnostics.generator as diagnostics_generator
from py_doc_tools.config.loader import load_config
from py_doc_tools.config.model import DiagnosticsConfig, DocToolsConfig
from py_doc_tools.core.console import Console
from py_doc_tools.core.exceptions import MissingConfigSectionError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

SUCCESS_CODE = 0
RUFF_FAILURE_CODE = 2
MKDOCS_FAILURE_CODE = 1
EXPECTED_CALL_COUNT = 2
COMMAND_NOT_FOUND_CODE = 1


def _make_config(**kwargs: object) -> DocToolsConfig:
    config_cls = cast("Callable[..., DocToolsConfig]", DocToolsConfig)
    return config_cls(**kwargs)


def _make_diagnostics_config(**kwargs: object) -> DiagnosticsConfig:
    config_cls = cast("Callable[..., DiagnosticsConfig]", DiagnosticsConfig)
    return config_cls(**kwargs)


def _base_config(
    tmp_path: Path,
    diagnostics: DiagnosticsConfig | None,
) -> DocToolsConfig:
    return _make_config(
        project_root=tmp_path,
        docs_dir=tmp_path / "docs",
        docs_src_dir=tmp_path / "docs",
        mkdocs_config=tmp_path / "mkdocs.yml",
        packages=["demo"],
        enable_diagnostics=diagnostics is not None,
        diagnostics=diagnostics,
    )


def _diagnostics_config(tmp_path: Path) -> DiagnosticsConfig:
    return _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=True,
        mkdocs_strict=True,
        ruff_targets=["src", "tests"],
        ruff_exclude_dirs=[".git", ".pixi", "docs/build"],
        ruff_exclude_files=["*.pyc"],
    )


def _assert_common_subprocess_kwargs(
    kwargs: Mapping[str, object],
    *,
    expected_cwd: Path,
) -> None:
    assert kwargs["cwd"] == expected_cwd
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"

    env = cast("dict[str, str]", kwargs["env"])
    assert env["PYTHONIOENCODING"] == "utf-8"
    assert env["PYTHONUTF8"] == "1"


def _assert_ruff_command(command: list[str]) -> None:
    assert command[:5] == [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "src",
    ]
    assert "tests" in command
    assert "--exclude" in command
    assert ".git" in command
    assert ".pixi" in command
    assert "docs/build" in command
    assert "*.pyc" in command


def test_generate_diagnostics_docs_runs_ruff_and_mkdocs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator captures Ruff and MkDocs outputs."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="ok stdout",
            stderr="ok stderr",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _diagnostics_config(tmp_path)
    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == SUCCESS_CODE
    assert len(calls) == EXPECTED_CALL_COUNT
    _assert_ruff_command(calls[0])
    assert "--strict" in calls[1]

    assert "Ruff diagnostics" in diagnostics.ruff_output_file.read_text(
        encoding="utf-8",
    )
    assert "MkDocs diagnostics" in diagnostics.mkdocs_output_file.read_text(
        encoding="utf-8",
    )


def test_generate_diagnostics_docs_is_non_blocking_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator does not fail on tool errors by default."""
    return_codes = [RUFF_FAILURE_CODE, MKDOCS_FAILURE_CODE]

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=return_codes.pop(0),
            stdout="",
            stderr="error",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    cfg = _base_config(tmp_path, _diagnostics_config(tmp_path))

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )


def test_generate_diagnostics_docs_returns_highest_exit_code_when_strict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator returns tool failures when fail_on options are set."""
    return_codes = [RUFF_FAILURE_CODE, MKDOCS_FAILURE_CODE]

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=return_codes.pop(0),
            stdout="",
            stderr="error",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=True,
        mkdocs_strict=True,
        fail_on_ruff=True,
        fail_on_mkdocs=True,
        ruff_targets=["src", "tests"],
        ruff_exclude_dirs=[".git", ".pixi", "docs/build"],
        ruff_exclude_files=["*.pyc"],
    )
    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console())
        == RUFF_FAILURE_CODE
    )


def test_generate_diagnostics_docs_can_disable_commands(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator respects enable flags."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=False,
        mkdocs_strict=False,
    )
    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )
    assert calls == []


def test_generate_diagnostics_docs_missing_config(tmp_path: Path) -> None:
    """Missing diagnostics config raises a dedicated error."""
    cfg = _base_config(tmp_path, None)

    with pytest.raises(MissingConfigSectionError, match="diagnostics"):
        _ = diagnostics_generator.generate_diagnostics_docs(cfg, Console())


def test_generate_diagnostics_docs_only_ruff_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator can run only Ruff."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="ruff only",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=False,
        mkdocs_strict=False,
        ruff_targets=["src", "tests"],
        ruff_exclude_dirs=[".git", ".pixi", "docs/build"],
        ruff_exclude_files=["*.pyc"],
    )

    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )
    assert len(calls) == 1
    _assert_ruff_command(calls[0])
    assert diagnostics.ruff_output_file.exists()
    assert not diagnostics.mkdocs_output_file.exists()


def test_generate_diagnostics_docs_only_mkdocs_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator can run only MkDocs."""
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        calls.append(command)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="mkdocs only",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=True,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    assert (
        diagnostics_generator.generate_diagnostics_docs(cfg, Console()) == SUCCESS_CODE
    )
    assert len(calls) == 1
    assert "mkdocs" in calls[0]
    assert not diagnostics.ruff_output_file.exists()
    assert diagnostics.mkdocs_output_file.exists()


def test_generate_diagnostics_docs_handles_missing_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator reports missing commands without crashing."""

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=False,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == SUCCESS_CODE
    assert diagnostics.ruff_output_file.exists()
    assert "could not be executed" in diagnostics.ruff_output_file.read_text(
        encoding="utf-8",
    )


def test_generate_diagnostics_docs_handles_missing_command_when_strict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator fails on missing Ruff command when strict."""

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=True,
        enable_mkdocs=False,
        mkdocs_strict=False,
        fail_on_ruff=True,
    )

    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == COMMAND_NOT_FOUND_CODE
    assert diagnostics.ruff_output_file.exists()


def test_generate_diagnostics_docs_handles_missing_mkdocs_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator reports missing MkDocs command without crashing."""

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=True,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == SUCCESS_CODE
    assert diagnostics.mkdocs_output_file.exists()
    assert "could not be executed" in diagnostics.mkdocs_output_file.read_text(
        encoding="utf-8",
    )


def test_load_diagnostics_config_reads_ruff_options(tmp_path: Path) -> None:
    """Diagnostics configuration reads Ruff targets and exclude patterns."""
    pyproject = tmp_path / "pyproject.toml"

    _ = pyproject.write_text(
        """
[tool.py-doc-tools]
enable_diagnostics = true

[tool.py-doc-tools.diagnostics]
output_dir = "docs/diagnostics"
ruff_output_file = "docs/diagnostics/ruff.md"
mkdocs_output_file = "docs/diagnostics/mkdocs.md"
enable_ruff = true
enable_mkdocs = false
mkdocs_strict = false
ruff_targets = ["src", "tests"]
ruff_exclude_dirs = [".git", ".pixi", "docs"]
ruff_exclude_files = ["*.pyc", "*.pyo"]
""",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)

    assert cfg.diagnostics is not None
    assert cfg.diagnostics.ruff_targets == ["src", "tests"]
    assert cfg.diagnostics.ruff_exclude_dirs == [".git", ".pixi", "docs"]
    assert cfg.diagnostics.ruff_exclude_files == ["*.pyc", "*.pyo"]


def test_generate_diagnostics_docs_parses_mkdocs_issues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Diagnostics generator renders parsed MkDocs issues."""
    source_file = tmp_path / "src" / "demo.py"
    source_file.parent.mkdir()
    _ = source_file.write_text("def demo(value):\n    return value\n", encoding="utf-8")

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        _assert_common_subprocess_kwargs(kwargs, expected_cwd=tmp_path)

        return subprocess.CompletedProcess[str](
            args=command,
            returncode=SUCCESS_CODE,
            stdout="WARNING -  src/demo.py:1: Missing type annotation\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    diagnostics = _make_diagnostics_config(
        output_dir=tmp_path / "docs" / "diagnostics",
        ruff_output_file=tmp_path / "docs" / "diagnostics" / "ruff.md",
        mkdocs_output_file=tmp_path / "docs" / "diagnostics" / "mkdocs.md",
        enable_ruff=False,
        enable_mkdocs=True,
        mkdocs_strict=False,
    )

    cfg = _base_config(tmp_path, diagnostics)

    code = diagnostics_generator.generate_diagnostics_docs(cfg, Console())

    assert code == SUCCESS_CODE
    content = diagnostics.mkdocs_output_file.read_text(encoding="utf-8")
    assert "Parsed issues" in content
    assert "`TYPING`" in content
    assert "`src/demo.py`" in content
