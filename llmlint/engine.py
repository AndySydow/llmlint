"""Check execution engine with async dispatch via ThreadPoolExecutor.

This module manages the core lifecycle of llmlint:
- Holds module-level state (rules, store, executor) set by ``configure()``.
- Runs individual checks in a thread pool so the caller's hot path is never blocked.
- Persists results to the configured store in background threads.

Typical flow::

    configure(rules, store)          # called once by llmlint.init()
    run_checks_sync(output, ...)     # blocking — returns CheckResultSet
    run_checks_fire_and_forget(...)  # non-blocking — for @watch decorator
"""

from __future__ import annotations

import atexit
import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from llmlint.checks import REGISTRY, CheckResult
from llmlint.config import CheckConfig
from llmlint.store import Store

logger = logging.getLogger("llmlint")

# ---------------------------------------------------------------------------
# Module-level state — set by configure(), consumed by run_checks_*
# ---------------------------------------------------------------------------
_rules: list[CheckConfig] = []
_store: Store | None = None
_executor: ThreadPoolExecutor | None = None
_atexit_registered: bool = False


def configure(rules: list[CheckConfig], store: Store) -> None:
    """Initialise engine state.  Called once by ``llmlint.init()``.

    Safe to call multiple times — the previous executor is shut down
    (non-blocking) before a fresh one is created.
    """
    global _rules, _store, _executor, _atexit_registered
    _rules = rules
    _store = store
    if _executor is not None:
        _executor.shutdown(wait=False)
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llmlint")

    if not _atexit_registered:
        atexit.register(_shutdown)
        _atexit_registered = True


def _shutdown() -> None:
    """Drain the thread pool on interpreter exit."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None


# ---------------------------------------------------------------------------
# Hashing helper
# ---------------------------------------------------------------------------


def _sha256(text: str | None) -> str | None:
    """Return the hex SHA-256 digest of *text*, or ``None`` if *text* is ``None``."""
    if text is None:
        return None
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Single-check runner
# ---------------------------------------------------------------------------


def _run_single_check(config: CheckConfig, output: str, **context: object) -> CheckResult:
    """Execute one check, catching unexpected exceptions.

    Returns a ``CheckResult`` in all cases — a failing check never raises.
    """
    run_fn = REGISTRY.get(config.type)
    if not run_fn:
        return CheckResult(
            name=config.name,
            check_type=config.type,
            severity="fail",
            detail=f"Unknown check type: {config.type}",
        )

    start = time.perf_counter()
    try:
        result = run_fn(config, output, **context)
    except Exception as e:
        result = CheckResult(
            name=config.name,
            check_type=config.type,
            severity="fail",
            detail=f"Check raised: {e}",
        )
    result.latency_ms = (time.perf_counter() - start) * 1000
    return result


# ---------------------------------------------------------------------------
# Store-write helper (shared by sync and fire-and-forget paths)
# ---------------------------------------------------------------------------


def _write_results(
    results: list[CheckResult],
    output: str,
    input: str | None,
    model: str | None,
    meta: dict | None,
) -> None:
    """Persist a batch of check results to the configured store.

    Computes hashes once and writes each result. Store failures are
    logged as warnings — they must never propagate to the caller.
    """
    if not _store:
        return
    out_hash = _sha256(output)
    in_hash = _sha256(input)
    for r in results:
        _store.write(r, output_hash=out_hash, input_hash=in_hash, model=model, meta=meta)


# ---------------------------------------------------------------------------
# Result aggregation
# ---------------------------------------------------------------------------


@dataclass
class CheckResultSet:
    """Aggregated outcome of running all configured checks against one output.

    Access helpers::

        result_set.has_failures   # bool — any hard failures?
        result_set.failures       # list of CheckResult with severity "fail"
        result_set.warnings       # list of CheckResult with severity "warn"
    """

    results: list[CheckResult] = field(default_factory=list)

    # Eagerly computed in __post_init__ so repeated access is O(1).
    _failures: list[CheckResult] = field(init=False, repr=False, default_factory=list)
    _warnings: list[CheckResult] = field(init=False, repr=False, default_factory=list)

    def __post_init__(self) -> None:
        self._failures = [r for r in self.results if r.severity == "fail"]
        self._warnings = [r for r in self.results if r.severity == "warn"]

    @property
    def has_failures(self) -> bool:
        return len(self._failures) > 0

    @property
    def failures(self) -> list[CheckResult]:
        return self._failures

    @property
    def warnings(self) -> list[CheckResult]:
        return self._warnings


# ---------------------------------------------------------------------------
# Public runners
# ---------------------------------------------------------------------------


def run_checks_sync(
    output: str,
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> CheckResultSet:
    """Run every configured check and block until all finish.

    Results are returned immediately; store writes happen in background
    threads so the caller is not blocked by I/O.

    Raises ``RuntimeError`` if ``configure()`` has not been called.
    """
    if not _executor:
        raise RuntimeError("llmlint not initialized. Call llmlint.init() first.")

    futures = [_executor.submit(_run_single_check, rule, output, input=input, model=model) for rule in _rules]
    results = [f.result() for f in futures]
    result_set = CheckResultSet(results=results)

    _executor.submit(_write_results, results, output, input, model, meta)
    return result_set


def run_checks_fire_and_forget(
    output: str,
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> None:
    """Submit all checks to the thread pool without waiting.

    Used by the ``@watch`` decorator to achieve zero-latency impact.
    """
    if not _executor:
        logger.warning("llmlint not initialized. Skipping checks.")
        return

    def _run_all() -> None:
        results = [_run_single_check(rule, output, input=input, model=model) for rule in _rules]
        _write_results(results, output, input, model, meta)

    _executor.submit(_run_all)
