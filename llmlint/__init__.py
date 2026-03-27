"""llmlint — Declarative quality checks for LLM outputs.

Public API (four functions):

- ``init(store_url, rules_path)`` — configure the engine once at startup.
- ``check(output, ...)``          — run all rules synchronously, return results.
- ``watch(...)``                   — decorator that runs rules in background.
- ``load(rules_path)``            — load and validate rules without running checks.

Quick start::

    import llmlint

    llmlint.init(store_url="sqlite:///llmlint.db", rules_path="checks.yaml")

    result = llmlint.check('{"answer": "hello"}')
    if result.has_failures:
        print(result.failures)
"""

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
    """Configure llmlint with a persistence backend and a YAML rules file.

    Must be called before ``check()`` or ``@watch`` are used.  Safe to
    call more than once — each call replaces the previous configuration.

    Args:
        store_url: SQLAlchemy-style connection string.
            Supported schemes: ``sqlite:///path.db``.
        rules_path: Path to a YAML file containing check definitions.

    Raises:
        FileNotFoundError: If *rules_path* does not exist.
        pydantic.ValidationError: If the YAML content is invalid.
        ValueError: If *store_url* uses an unsupported scheme.
    """
    rules = load_rules(rules_path)
    store = get_store(store_url)
    configure(rules, store)


def check(
    output: str,
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> CheckResultSet:
    """Run all configured checks against *output* and return the results.

    This call blocks until every check has finished.  Store writes happen
    in background threads so they don't add latency.

    Args:
        output: The LLM-generated text to validate.
        input: The original user prompt (hashed for consistency tracking).
        model: Model identifier (e.g. ``"gpt-4"``), stored as metadata.
        meta: Arbitrary key/value pairs persisted alongside results.

    Returns:
        A ``CheckResultSet`` with ``.has_failures``, ``.failures``,
        ``.warnings``, and the full ``.results`` list.

    Raises:
        RuntimeError: If ``init()`` has not been called yet.
    """
    return run_checks_sync(output, input=input, model=model, meta=meta)


def watch(
    input: str | None = None,
    model: str | None = None,
    meta: dict | None = None,
) -> Callable:
    """Decorator that runs checks in background after the wrapped function returns.

    Zero latency impact — checks are submitted to a thread pool and the
    original return value is passed through immediately.

    Args:
        input: Optional prompt text for consistency tracking.
        model: Model identifier stored as metadata.
        meta: Arbitrary key/value pairs persisted alongside results.

    Example::

        @llmlint.watch(model="gpt-4")
        def generate(prompt: str) -> str:
            return call_llm(prompt)
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
    """Load and validate check rules from a YAML file without running them.

    Useful for CI validation of rule files or editor tooling.

    Args:
        rules_path: Path to the YAML rules file.

    Returns:
        A list of typed check-config objects (one per rule).

    Raises:
        FileNotFoundError: If *rules_path* does not exist.
        pydantic.ValidationError: If the YAML content is invalid.
    """
    return load_rules(rules_path)
