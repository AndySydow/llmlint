"""llmlint — Declarative quality checks for LLM outputs."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from llmlint.config import CheckConfig, load_rules
from llmlint.engine import CheckResultSet, configure, run_checks_fire_and_forget, run_checks_sync
from llmlint.store import get_store

__all__ = ["init", "check", "watch", "load"]


def init(
    store_url: str = "sqlite:///llmlint.db",
    rules_path: str | Path = "checks.yaml",
) -> None:
    """Initialize llmlint with a store backend and rules file."""
    rules = load_rules(rules_path)
    store = get_store(store_url)
    configure(rules, store)


def check(
    output: str,
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> CheckResultSet:
    """Run all configured checks against output. Blocking — returns results."""
    return run_checks_sync(output, input=input, model=model, meta=meta)


def watch(
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> Callable:
    """Decorator that runs checks in background after the wrapped function returns.

    Zero latency impact — checks run fire-and-forget in a thread pool.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            output_text = result if isinstance(result, str) else str(result)
            run_checks_fire_and_forget(output_text, input=input, model=model, meta=meta)
            return result

        return wrapper

    return decorator


def load(rules_path: str | Path) -> list[CheckConfig]:
    """Load and validate rules from a YAML file without running checks."""
    return load_rules(rules_path)
