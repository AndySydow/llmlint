"""Store interface and factory."""

from __future__ import annotations

from typing import Protocol

from llmlint.checks import CheckResult


class Store(Protocol):
    def write(
        self,
        result: CheckResult,
        output_text: str | None = None,
        output_hash: str | None = None,
        input_hash: str | None = None,
        model: str | None = None,
        meta: dict | None = None,
    ) -> None: ...

    def ensure_tables(self) -> None: ...


def get_store(url: str) -> Store:
    """Create a store backend from a connection URL."""
    if url.startswith("sqlite"):
        from llmlint.store.sqlite import SqliteStore

        return SqliteStore(url)
    raise ValueError(f"Unsupported store URL: {url}")
