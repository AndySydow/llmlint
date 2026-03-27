"""Check runner with async dispatch via ThreadPoolExecutor."""

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

# Module-level state, set by configure()
_rules: list[CheckConfig] = []
_store: Store | None = None
_executor: ThreadPoolExecutor | None = None


def configure(rules: list[CheckConfig], store: Store) -> None:
    """Initialize engine state. Called by llmlint.init()."""
    global _rules, _store, _executor
    _rules = rules
    _store = store
    if _executor is not None:
        _executor.shutdown(wait=False)
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llmlint")
    atexit.register(_shutdown)


def _shutdown() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None


def _sha256(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode()).hexdigest()


def _run_single_check(config: CheckConfig, output: str, **context: object) -> CheckResult:
    """Run one check, catching all exceptions."""
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


@dataclass
class CheckResultSet:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(r.severity == "fail" for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == "fail"]

    @property
    def warnings(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == "warn"]


def run_checks_sync(
    output: str,
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> CheckResultSet:
    """Run all checks, wait for results, write to store in background. Blocking."""
    if not _executor:
        raise RuntimeError("llmlint not initialized. Call llmlint.init() first.")

    futures = [_executor.submit(_run_single_check, rule, output, input=input, model=model) for rule in _rules]
    results = [f.result() for f in futures]
    result_set = CheckResultSet(results=results)

    # Write to store in background
    if _store:
        out_hash = _sha256(output)
        in_hash = _sha256(input)
        for r in results:
            _executor.submit(_store.write, r, output_hash=out_hash, input_hash=in_hash, model=model, meta=meta)

    return result_set


def run_checks_fire_and_forget(
    output: str,
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> None:
    """Submit checks to thread pool, do not wait. For @watch."""
    if not _executor:
        logger.warning("llmlint not initialized. Skipping checks.")
        return

    def _run_all() -> None:
        out_hash = _sha256(output)
        in_hash = _sha256(input)
        for rule in _rules:
            result = _run_single_check(rule, output, input=input, model=model)
            if _store:
                _store.write(result, output_hash=out_hash, input_hash=in_hash, model=model, meta=meta)

    _executor.submit(_run_all)
