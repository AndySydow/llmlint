"""SQLite persistence backend using SQLAlchemy Core.

Stores check results in a single ``check_results`` table.  Writes are
designed to be called from background threads — failures are logged as
warnings and never propagate to the caller.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import sqlalchemy as sa

from llmlint.checks import CheckResult

logger = logging.getLogger("llmlint")

metadata = sa.MetaData()

check_results = sa.Table(
    "check_results",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("timestamp", sa.DateTime, nullable=False),
    sa.Column("check_name", sa.String, nullable=False),
    sa.Column("check_type", sa.String, nullable=False),
    sa.Column("severity", sa.String, nullable=False),
    sa.Column("output_text", sa.Text, nullable=True),
    sa.Column("output_hash", sa.String(64), nullable=True),
    sa.Column("input_hash", sa.String(64), nullable=True),
    sa.Column("model", sa.String, nullable=True),
    sa.Column("meta", sa.Text, nullable=True),
    sa.Column("failure_detail", sa.Text, nullable=True),
    sa.Column("latency_ms", sa.Float, nullable=True),
    # Populated by performance checks (M2)
    sa.Column("input_tokens", sa.Integer, nullable=True),
    sa.Column("output_tokens", sa.Integer, nullable=True),
    sa.Column("cost_usd", sa.Float, nullable=True),
)

# Indexes for common query patterns (filtering by time, check name, severity)
sa.Index("ix_check_results_timestamp", check_results.c.timestamp)
sa.Index("ix_check_results_check_name", check_results.c.check_name)
sa.Index("ix_check_results_severity", check_results.c.severity)


class SqliteStore:
    """SQLite-backed store for check results.

    Creates the schema on instantiation.  Each ``write()`` opens its own
    connection and commits immediately — safe to call from any thread.
    """

    def __init__(self, url: str) -> None:
        self._engine = sa.create_engine(url)
        self.ensure_tables()

    def ensure_tables(self) -> None:
        """Create tables and indexes if they don't already exist."""
        metadata.create_all(self._engine)

    def write(
        self,
        result: CheckResult,
        output_text: str | None = None,
        output_hash: str | None = None,
        input_hash: str | None = None,
        model: str | None = None,
        meta: dict | None = None,
    ) -> None:
        """Persist a single check result.

        Catches all exceptions and logs a warning — store failures must
        never crash the caller's application.
        """
        try:
            with self._engine.connect() as conn:
                conn.execute(
                    check_results.insert().values(
                        timestamp=datetime.now(timezone.utc),
                        check_name=result.name,
                        check_type=result.check_type,
                        severity=result.severity,
                        output_text=output_text,
                        output_hash=output_hash,
                        input_hash=input_hash,
                        model=model,
                        meta=json.dumps(meta) if meta else None,
                        failure_detail=result.detail,
                        latency_ms=result.latency_ms,
                    )
                )
                conn.commit()
        except Exception:
            logger.warning("Failed to write check result to store", exc_info=True)
