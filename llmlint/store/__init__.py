"""Store interface and factory.

All persistence backends implement the ``Store`` protocol — a single
``write()`` method plus ``ensure_tables()`` for schema setup.

Use ``get_store(url)`` to obtain the right backend from a connection
string::

    store = get_store("sqlite:///llmlint.db")
"""

from __future__ import annotations

from typing import Protocol

from llmlint.checks import CheckResult


class Store(Protocol):
    """Minimal persistence interface for check results.

    Implementations must be **thread-safe** — the engine calls ``write()``
    from background threads.
    """

    def write(
        self,
        result: CheckResult,
        output_text: str | None = None,
        output_hash: str | None = None,
        input_hash: str | None = None,
        model: str | None = None,
        meta: dict | None = None,
    ) -> None:
        """Persist a single check result."""
        ...

    def ensure_tables(self) -> None:
        """Create tables/indexes if they don't already exist."""
        ...


def get_store(url: str) -> Store:
    """Instantiate a store backend from a connection URL.

    Args:
        url: SQLAlchemy-style connection string.
            Supported: ``sqlite:///…``

    Raises:
        ValueError: If the URL scheme is not supported.
    """
    if url.startswith("sqlite"):
        from llmlint.store.sqlite import SqliteStore

        return SqliteStore(url)
    raise ValueError(f"Unsupported store URL: {url}")
