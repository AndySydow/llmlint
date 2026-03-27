"""Tests for pattern check."""

from llmlint.checks.pattern import run
from llmlint.config import PatternCheckConfig


def _config(**kwargs):
    return PatternCheckConfig(type="pattern", name="test_pattern", **kwargs)


def test_must_match_present():
    result = run(_config(must_match=[r"hello"]), "hello world")
    assert result.severity == "pass"


def test_must_match_absent():
    result = run(_config(must_match=[r"goodbye"]), "hello world")
    assert result.severity == "fail"
    assert "Required pattern not found" in result.detail


def test_must_not_match_absent():
    result = run(_config(must_not_match=[r"\d{3}-\d{2}-\d{4}"]), "no ssn here")
    assert result.severity == "pass"


def test_must_not_match_present():
    result = run(_config(must_not_match=[r"\d{3}-\d{2}-\d{4}"]), "SSN: 123-45-6789")
    assert result.severity == "fail"
    assert "Blocked pattern matched" in result.detail
    assert "123-45-6789" in result.detail


def test_multiple_must_match_all_present():
    result = run(_config(must_match=[r"hello", r"world"]), "hello world")
    assert result.severity == "pass"


def test_multiple_must_match_one_missing():
    result = run(_config(must_match=[r"hello", r"goodbye"]), "hello world")
    assert result.severity == "fail"
    assert "goodbye" in result.detail


def test_multiple_must_not_match_none_present():
    result = run(_config(must_not_match=[r"SSN", r"password"]), "clean text")
    assert result.severity == "pass"


def test_multiple_must_not_match_one_present():
    result = run(_config(must_not_match=[r"SSN", r"password"]), "your password is 123")
    assert result.severity == "fail"
    assert "password" in result.detail


def test_no_patterns_passes():
    result = run(_config(), "anything")
    assert result.severity == "pass"


def test_email_pattern():
    result = run(
        _config(must_not_match=[r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"]),
        "contact me at user@example.com",
    )
    assert result.severity == "fail"


def test_severity_warn():
    result = run(_config(severity="warn", must_match=[r"\[citation\]"]), "no citation here")
    assert result.severity == "warn"


def test_regex_search_not_match():
    """Patterns use re.search, so they don't need to match from the start."""
    result = run(_config(must_match=[r"world"]), "hello world")
    assert result.severity == "pass"
