"""Tests for the CLI."""

from importlib.metadata import version

from click.testing import CliRunner

from llmlint.cli import main


def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "llmlint" in result.output


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert version("llmlint") in result.output
