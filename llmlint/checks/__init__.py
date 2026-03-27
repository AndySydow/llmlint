"""Check registry and shared result type.

Every check module exposes a ``run(config, output, **context) -> CheckResult``
function.  The ``REGISTRY`` dict maps check-type strings (matching the
``type`` discriminator in config models) to those functions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Outcome of a single check execution.

    Attributes:
        name: Human-readable check name (from the YAML rule).
        check_type: Registry key — ``"schema"``, ``"length"``, etc.
        severity: ``"pass"`` | ``"warn"`` | ``"fail"``.
        detail: Explanation when the check did not pass (``None`` on pass).
        latency_ms: Wall-clock time spent in the check (set by the engine).
    """

    name: str
    check_type: str
    severity: str
    detail: str | None = None
    latency_ms: float = 0.0


def _build_registry() -> dict[str, Callable]:
    """Import check modules and return the type -> run-function mapping.

    Kept in a function so the imports happen once at module-load time
    without polluting the module namespace with check-module references.
    """
    from llmlint.checks import json_valid, length, pattern, refusal, schema

    return {
        "schema": schema.run,
        "length": length.run,
        "pattern": pattern.run,
        "json_valid": json_valid.run,
        "refusal": refusal.run,
    }


REGISTRY: dict[str, Callable] = _build_registry()
