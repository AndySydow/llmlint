"""Tests for the store layer."""

import logging

import pytest
import sqlalchemy as sa

from llmlint.checks import CheckResult
from llmlint.store import get_store
from llmlint.store.sqlite import SqliteStore, check_results


@pytest.fixture
def memory_store():
    return SqliteStore("sqlite:///:memory:")


@pytest.fixture
def sample_result():
    return CheckResult(
        name="test_check",
        check_type="length",
        severity="fail",
        detail="Too short: 3 chars < min 10",
        latency_ms=1.5,
    )


def test_ensure_tables(memory_store):
    """Tables are created on init."""
    insp = sa.inspect(memory_store._engine)
    assert "check_results" in insp.get_table_names()


def test_write_and_read_back(memory_store, sample_result):
    memory_store.write(
        sample_result,
        output_text="hi",
        output_hash="abc123",
        input_hash="def456",
        model="gpt-4",
        meta={"key": "value"},
    )

    with memory_store._engine.connect() as conn:
        rows = conn.execute(sa.select(check_results)).fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row.check_name == "test_check"
    assert row.check_type == "length"
    assert row.severity == "fail"
    assert row.output_text == "hi"
    assert row.output_hash == "abc123"
    assert row.input_hash == "def456"
    assert row.model == "gpt-4"
    assert '"key"' in row.meta
    assert row.failure_detail == "Too short: 3 chars < min 10"
    assert row.latency_ms == 1.5
    assert row.timestamp is not None


def test_write_minimal(memory_store):
    result = CheckResult(name="minimal", check_type="schema", severity="pass")
    memory_store.write(result)

    with memory_store._engine.connect() as conn:
        rows = conn.execute(sa.select(check_results)).fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row.output_text is None
    assert row.meta is None
    assert row.failure_detail is None


def test_write_multiple(memory_store, sample_result):
    for _ in range(5):
        memory_store.write(sample_result)

    with memory_store._engine.connect() as conn:
        count = conn.execute(sa.select(sa.func.count()).select_from(check_results)).scalar()

    assert count == 5


def test_write_failure_logs_warning(memory_store, sample_result, caplog):
    """Store write failures should log a warning, not raise."""
    # Drop the table to cause a write failure
    with memory_store._engine.connect() as conn:
        conn.execute(sa.text("DROP TABLE check_results"))
        conn.commit()

    with caplog.at_level(logging.WARNING, logger="llmlint"):
        memory_store.write(sample_result)  # should not raise

    assert "Failed to write" in caplog.text


def test_get_store_sqlite():
    store = get_store("sqlite:///:memory:")
    assert isinstance(store, SqliteStore)


def test_get_store_unsupported():
    with pytest.raises(ValueError, match="Unsupported store URL"):
        get_store("mongodb://localhost/db")
