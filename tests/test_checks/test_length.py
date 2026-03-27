"""Tests for length check."""

from unittest.mock import MagicMock, patch

from llmlint.checks.length import run
from llmlint.config import LengthCheckConfig


def _config(**kwargs):
    return LengthCheckConfig(type="length", name="test_length", **kwargs)


def test_within_char_bounds():
    result = run(_config(min_chars=5, max_chars=100), "hello world")
    assert result.severity == "pass"


def test_too_short():
    result = run(_config(min_chars=20), "short")
    assert result.severity == "fail"
    assert "Too short" in result.detail
    assert "5 chars" in result.detail


def test_too_long():
    result = run(_config(max_chars=5), "this is way too long")
    assert result.severity == "fail"
    assert "Too long" in result.detail


def test_no_bounds_always_passes():
    result = run(_config(), "anything goes")
    assert result.severity == "pass"


def test_exact_min_boundary():
    result = run(_config(min_chars=5), "12345")
    assert result.severity == "pass"


def test_exact_max_boundary():
    result = run(_config(max_chars=5), "12345")
    assert result.severity == "pass"


def test_empty_string_with_min():
    result = run(_config(min_chars=1), "")
    assert result.severity == "fail"


def test_severity_warn():
    result = run(_config(severity="warn", max_chars=5), "too long text")
    assert result.severity == "warn"


def test_token_counting_without_tiktoken():
    with patch.dict("sys.modules", {"tiktoken": None}):
        # Force reimport to trigger ImportError
        import importlib

        import llmlint.checks.length as mod

        importlib.reload(mod)
        result = mod.run(_config(min_tokens=5), "hello")
        assert result.severity == "fail"
        assert "llmlint[tokens]" in result.detail
        # Reload again to restore
        importlib.reload(mod)


def test_token_counting_with_mock_tiktoken():
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens

    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.return_value = mock_enc

    with patch.dict("sys.modules", {"tiktoken": mock_tiktoken}):
        import importlib

        import llmlint.checks.length as mod

        importlib.reload(mod)
        result = mod.run(_config(min_tokens=3, max_tokens=10), "hello world")
        assert result.severity == "pass"
        importlib.reload(mod)


def test_token_too_few_with_mock():
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [1, 2]  # 2 tokens

    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.return_value = mock_enc

    with patch.dict("sys.modules", {"tiktoken": mock_tiktoken}):
        import importlib

        import llmlint.checks.length as mod

        importlib.reload(mod)
        result = mod.run(_config(min_tokens=5), "hi")
        assert result.severity == "fail"
        assert "Too few tokens" in result.detail
        importlib.reload(mod)


def test_token_too_many_with_mock():
    mock_enc = MagicMock()
    mock_enc.encode.return_value = list(range(20))  # 20 tokens

    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.return_value = mock_enc

    with patch.dict("sys.modules", {"tiktoken": mock_tiktoken}):
        import importlib

        import llmlint.checks.length as mod

        importlib.reload(mod)
        result = mod.run(_config(max_tokens=10), "long text here")
        assert result.severity == "fail"
        assert "Too many tokens" in result.detail
        importlib.reload(mod)
