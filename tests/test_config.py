"""Tests for YAML config loading and pydantic validation."""

import pytest
from pydantic import ValidationError

from llmlint.config import (
    LengthCheckConfig,
    PatternCheckConfig,
    RefusalCheckConfig,
    RulesFile,
    load_rules,
)


def test_load_rules_basic(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(
        """
checks:
  - type: length
    name: not_too_long
    max_chars: 1000
"""
    )
    rules = load_rules(yaml_file)
    assert len(rules) == 1
    assert isinstance(rules[0], LengthCheckConfig)
    assert rules[0].name == "not_too_long"
    assert rules[0].max_chars == 1000
    assert rules[0].severity == "fail"  # default


def test_load_rules_multiple_checks(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(
        """
checks:
  - type: length
    name: len_check
    min_chars: 10
  - type: pattern
    name: no_pii
    must_not_match:
      - '\\d{3}-\\d{2}-\\d{4}'
  - type: json_valid
    name: valid_json
  - type: refusal
    name: no_refusal
  - type: schema
    name: api_schema
    json_schema:
      type: object
      required: [answer]
"""
    )
    rules = load_rules(yaml_file)
    assert len(rules) == 5


def test_severity_override(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(
        """
checks:
  - type: length
    name: soft_length
    severity: warn
    max_chars: 500
"""
    )
    rules = load_rules(yaml_file)
    assert rules[0].severity == "warn"


def test_invalid_severity():
    with pytest.raises(ValidationError):
        RulesFile.model_validate(
            {"checks": [{"type": "length", "name": "bad", "severity": "critical", "max_chars": 100}]}
        )


def test_unknown_check_type():
    with pytest.raises(ValidationError):
        RulesFile.model_validate({"checks": [{"type": "unknown_type", "name": "bad"}]})


def test_missing_name():
    with pytest.raises(ValidationError):
        RulesFile.model_validate({"checks": [{"type": "length", "max_chars": 100}]})


def test_schema_check_requires_json_schema():
    with pytest.raises(ValidationError):
        RulesFile.model_validate({"checks": [{"type": "schema", "name": "bad"}]})


def test_length_defaults():
    config = LengthCheckConfig(type="length", name="test")
    assert config.min_chars is None
    assert config.max_chars is None
    assert config.min_tokens is None
    assert config.max_tokens is None
    assert config.tokenizer == "cl100k_base"


def test_pattern_defaults():
    config = PatternCheckConfig(type="pattern", name="test")
    assert config.must_match == []
    assert config.must_not_match == []


def test_refusal_defaults():
    config = RefusalCheckConfig(type="refusal", name="test")
    assert len(config.phrases) > 0
    assert config.threshold == 1


def test_load_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_rules("/nonexistent/path.yaml")


def test_empty_checks_list(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text("checks: []\n")
    rules = load_rules(yaml_file)
    assert rules == []
