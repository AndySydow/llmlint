"""Check registry and result type."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    check_type: str
    severity: str  # "pass", "warn", "fail"
    detail: str | None = None
    latency_ms: float = 0.0


REGISTRY: dict[str, Callable] = {}


def _register() -> None:
    from llmlint.checks import json_valid, length, pattern, refusal, schema

    REGISTRY["schema"] = schema.run
    REGISTRY["length"] = length.run
    REGISTRY["pattern"] = pattern.run
    REGISTRY["json_valid"] = json_valid.run
    REGISTRY["refusal"] = refusal.run


_register()
