"""Tests for schema check."""

from llmlint.checks.schema import run
from llmlint.config import SchemaCheckConfig

SCHEMA = {
    "type": "object",
    "required": ["answer", "confidence"],
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


def _config(**kwargs):
    return SchemaCheckConfig(type="schema", name="test_schema", json_schema=SCHEMA, **kwargs)


def test_valid_json_matching_schema():
    result = run(_config(), '{"answer": "hello", "confidence": 0.9}')
    assert result.severity == "pass"
    assert result.detail is None


def test_valid_json_not_matching_schema():
    result = run(_config(), '{"answer": "hello"}')
    assert result.severity == "fail"
    assert "confidence" in result.detail


def test_invalid_json():
    result = run(_config(), "not json at all")
    assert result.severity == "fail"
    assert "not valid JSON" in result.detail


def test_empty_string():
    result = run(_config(), "")
    assert result.severity == "fail"


def test_wrong_type_in_schema():
    result = run(_config(), '{"answer": 123, "confidence": 0.5}')
    assert result.severity == "fail"
    assert "Schema validation failed" in result.detail


def test_confidence_out_of_range():
    result = run(_config(), '{"answer": "hello", "confidence": 1.5}')
    assert result.severity == "fail"


def test_severity_warn():
    result = run(_config(severity="warn"), '{"answer": "hello"}')
    assert result.severity == "warn"


def test_check_type_field():
    result = run(_config(), '{"answer": "hello", "confidence": 0.5}')
    assert result.check_type == "schema"
    assert result.name == "test_schema"
