"""Tests for refusal check."""

from llmlint.checks.refusal import run
from llmlint.config import RefusalCheckConfig


def _config(**kwargs):
    return RefusalCheckConfig(type="refusal", name="test_refusal", **kwargs)


def test_no_refusal():
    result = run(_config(), "Here is the information you requested.")
    assert result.severity == "pass"


def test_single_refusal_phrase():
    result = run(_config(), "I cannot help with that request.")
    assert result.severity == "fail"
    assert "I cannot" in result.detail


def test_case_insensitive():
    result = run(_config(), "I CANNOT help with that.")
    assert result.severity == "fail"


def test_threshold_above_one():
    result = run(_config(threshold=2), "I cannot do that.")
    assert result.severity == "pass"  # only 1 match, threshold is 2


def test_threshold_met():
    result = run(_config(threshold=2), "I cannot do that. I'm unable to help.")
    assert result.severity == "fail"


def test_custom_phrases():
    result = run(
        _config(phrases=["BLOCKED", "DENIED"]),
        "Your request has been DENIED.",
    )
    assert result.severity == "fail"
    assert "DENIED" in result.detail


def test_custom_phrases_no_match():
    result = run(
        _config(phrases=["BLOCKED", "DENIED"]),
        "Here is your answer.",
    )
    assert result.severity == "pass"


def test_multiple_matches_reported():
    result = run(_config(), "I cannot help. As an AI, I'm unable to do that.")
    assert result.severity == "fail"
    assert "3 match" in result.detail


def test_severity_warn():
    result = run(_config(severity="warn"), "I cannot help.")
    assert result.severity == "warn"


def test_empty_output():
    result = run(_config(), "")
    assert result.severity == "pass"


def test_default_phrases_populated():
    config = _config()
    assert len(config.phrases) > 0


def test_check_type_field():
    result = run(_config(), "hello")
    assert result.check_type == "refusal"
    assert result.name == "test_refusal"
