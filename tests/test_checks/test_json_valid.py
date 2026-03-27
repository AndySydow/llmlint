"""Tests for json_valid check."""

from llmlint.checks.json_valid import run
from llmlint.config import JsonValidCheckConfig


def _config(**kwargs):
    return JsonValidCheckConfig(type="json_valid", name="test_json", **kwargs)


def test_valid_json():
    result = run(_config(), '{"key": "value"}')
    assert result.severity == "pass"


def test_valid_json_array():
    result = run(_config(), "[1, 2, 3]")
    assert result.severity == "pass"


def test_invalid_json():
    result = run(_config(), "not json")
    assert result.severity == "fail"
    assert "Invalid JSON" in result.detail


def test_empty_string():
    result = run(_config(), "")
    assert result.severity == "fail"


def test_markdown_fences_stripped():
    result = run(_config(), '```json\n{"key": "value"}\n```')
    assert result.severity == "pass"


def test_markdown_fences_without_language():
    result = run(_config(), '```\n{"key": "value"}\n```')
    assert result.severity == "pass"


def test_markdown_fences_disabled():
    result = run(_config(strip_markdown_fences=False), '```json\n{"key": "value"}\n```')
    assert result.severity == "fail"


def test_json_with_whitespace():
    result = run(_config(), '  \n  {"key": "value"}  \n  ')
    assert result.severity == "pass"


def test_nested_json():
    result = run(_config(), '{"outer": {"inner": [1, 2, 3]}}')
    assert result.severity == "pass"


def test_json_string_literal():
    result = run(_config(), '"just a string"')
    assert result.severity == "pass"


def test_json_number():
    result = run(_config(), "42")
    assert result.severity == "pass"


def test_severity_warn():
    result = run(_config(severity="warn"), "not json")
    assert result.severity == "warn"


def test_check_type_field():
    result = run(_config(), '{"key": "value"}')
    assert result.check_type == "json_valid"
