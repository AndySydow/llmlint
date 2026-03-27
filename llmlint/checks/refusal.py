"""Refusal detection via substring matching."""

from __future__ import annotations

from llmlint.checks import CheckResult
from llmlint.config import RefusalCheckConfig


def run(config: RefusalCheckConfig, output: str, **context: object) -> CheckResult:
    """Detect refusal phrases in output via case-insensitive substring matching."""
    output_lower = output.lower()
    matched = [phrase for phrase in config.phrases if phrase.lower() in output_lower]

    if len(matched) >= config.threshold:
        return CheckResult(
            name=config.name,
            check_type="refusal",
            severity=config.severity,
            detail=f"Refusal detected ({len(matched)} match(es)): {matched}",
        )

    return CheckResult(name=config.name, check_type="refusal", severity="pass")
