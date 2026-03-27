"""Tests for the check engine."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from llmlint.checks import CheckResult
from llmlint.config import LengthCheckConfig, PatternCheckConfig
from llmlint.engine import (
    CheckResultSet,
    _run_single_check,
    _sha256,
    configure,
    run_checks_fire_and_forget,
    run_checks_sync,
)
from llmlint.store.sqlite import SqliteStore


@pytest.fixture
def store():
    return SqliteStore("sqlite:///:memory:")


@pytest.fixture
def simple_rules():
    return [
        LengthCheckConfig(type="length", name="len_check", min_chars=5, max_chars=100),
        PatternCheckConfig(type="pattern", name="pat_check", must_not_match=[r"\d{3}-\d{2}-\d{4}"]),
    ]


@pytest.fixture
def configured_engine(store, simple_rules):
    configure(simple_rules, store)
    yield
    # Reset state
    configure([], store)


def test_run_single_check_pass():
    config = LengthCheckConfig(type="length", name="test", min_chars=3)
    result = _run_single_check(config, "hello world")
    assert result.severity == "pass"
    assert result.latency_ms > 0


def test_run_single_check_fail():
    config = LengthCheckConfig(type="length", name="test", min_chars=100)
    result = _run_single_check(config, "short")
    assert result.severity == "fail"


def test_run_single_check_unknown_type():
    # Create a mock config with an unknown type
    config = LengthCheckConfig(type="length", name="test")
    config.__dict__["type"] = "nonexistent"
    result = _run_single_check(config, "hello")
    assert result.severity == "fail"
    assert "Unknown check type" in result.detail


def test_sha256():
    assert _sha256("hello") is not None
    assert len(_sha256("hello")) == 64
    assert _sha256(None) is None
    assert _sha256("hello") == _sha256("hello")
    assert _sha256("hello") != _sha256("world")


def test_check_result_set():
    results = [
        CheckResult(name="a", check_type="length", severity="pass"),
        CheckResult(name="b", check_type="length", severity="fail", detail="too short"),
        CheckResult(name="c", check_type="length", severity="warn", detail="borderline"),
        CheckResult(name="d", check_type="length", severity="fail", detail="too long"),
    ]
    rs = CheckResultSet(results=results)
    assert rs.has_failures
    assert len(rs.failures) == 2
    assert len(rs.warnings) == 1


def test_check_result_set_no_failures():
    results = [
        CheckResult(name="a", check_type="length", severity="pass"),
        CheckResult(name="b", check_type="length", severity="warn"),
    ]
    rs = CheckResultSet(results=results)
    assert not rs.has_failures
    assert len(rs.failures) == 0
    assert len(rs.warnings) == 1


def test_run_checks_sync(configured_engine):
    result_set = run_checks_sync("hello world")
    assert len(result_set.results) == 2
    assert not result_set.has_failures


def test_run_checks_sync_with_failure(configured_engine):
    result_set = run_checks_sync("hi")  # too short (min_chars=5)
    assert result_set.has_failures
    assert len(result_set.failures) == 1


def test_run_checks_sync_not_initialized():
    from llmlint import engine

    old_executor = engine._executor
    engine._executor = None
    with pytest.raises(RuntimeError, match="not initialized"):
        run_checks_sync("hello")
    engine._executor = old_executor


def test_run_checks_sync_writes_to_store(tmp_path, simple_rules):
    db_path = tmp_path / "test.db"
    store = SqliteStore(f"sqlite:///{db_path}")
    configure(simple_rules, store)
    run_checks_sync("hello world", model="gpt-4", meta={"test": True})

    # Shut down executor to flush pending background writes
    from llmlint import engine

    engine._executor.shutdown(wait=True)
    engine._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llmlint")

    import sqlalchemy as sa

    from llmlint.store.sqlite import check_results

    with store._engine.connect() as conn:
        count = conn.execute(sa.select(sa.func.count()).select_from(check_results)).scalar()
    assert count == 2  # one per rule


def test_fire_and_forget(store, simple_rules):
    configure(simple_rules, store)
    done = threading.Event()

    original_write = store.write

    def write_and_signal(*args, **kwargs):
        original_write(*args, **kwargs)
        done.set()

    store.write = write_and_signal

    run_checks_fire_and_forget("hello world")

    # Should return immediately — verify store gets written eventually
    assert done.wait(timeout=2.0)


def test_fire_and_forget_not_initialized(caplog):
    from llmlint import engine

    old_executor = engine._executor
    engine._executor = None
    import logging

    with caplog.at_level(logging.WARNING, logger="llmlint"):
        run_checks_fire_and_forget("hello")
    assert "not initialized" in caplog.text
    engine._executor = old_executor


def test_configure_replaces_executor(store, simple_rules):
    configure(simple_rules, store)
    from llmlint import engine

    first_executor = engine._executor
    configure(simple_rules, store)
    second_executor = engine._executor
    assert second_executor is not first_executor


def test_run_single_check_catches_exception():
    """Check that raises an exception returns a fail result."""
    from unittest.mock import patch

    from llmlint.checks import REGISTRY

    def bad_check(config, output, **ctx):
        raise ValueError("something broke")

    config = LengthCheckConfig(type="length", name="broken")
    with patch.dict(REGISTRY, {"length": bad_check}):
        result = _run_single_check(config, "hello")
    assert result.severity == "fail"
    assert "Check raised" in result.detail
    assert "something broke" in result.detail


def test_shutdown():
    from llmlint.engine import _shutdown

    store = SqliteStore("sqlite:///:memory:")
    configure([], store)
    from llmlint import engine

    assert engine._executor is not None
    _shutdown()
    assert engine._executor is None
