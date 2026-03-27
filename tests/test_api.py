"""Tests for the public API (llmlint.init, check, watch, load)."""

import llmlint
from llmlint.config import LengthCheckConfig


def test_load(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(
        """
checks:
  - type: length
    name: test
    min_chars: 5
"""
    )
    rules = llmlint.load(yaml_file)
    assert len(rules) == 1
    assert isinstance(rules[0], LengthCheckConfig)


def test_init_and_check(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(
        """
checks:
  - type: length
    name: not_too_short
    min_chars: 5
  - type: json_valid
    name: is_json
"""
    )
    db_path = tmp_path / "test.db"
    llmlint.init(store_url=f"sqlite:///{db_path}", rules_path=yaml_file)

    result = llmlint.check('{"key": "value"}')
    assert not result.has_failures
    assert len(result.results) == 2

    result = llmlint.check("hi")
    assert result.has_failures
    assert len(result.failures) == 2  # too short + not json


def test_watch_decorator(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(
        """
checks:
  - type: length
    name: len
    min_chars: 1
"""
    )
    db_path = tmp_path / "test_watch.db"
    llmlint.init(store_url=f"sqlite:///{db_path}", rules_path=yaml_file)

    @llmlint.watch()
    def generate():
        return "hello world"

    result = generate()
    assert result == "hello world"  # original return value preserved


def test_watch_non_string_return(tmp_path):
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text("checks:\n  - type: length\n    name: len\n    min_chars: 1\n")
    db_path = tmp_path / "test_watch2.db"
    llmlint.init(store_url=f"sqlite:///{db_path}", rules_path=yaml_file)

    @llmlint.watch()
    def generate_dict():
        return {"answer": "hello"}

    result = generate_dict()
    assert result == {"answer": "hello"}
