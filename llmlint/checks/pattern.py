"""Regex match and blocklist check.

Uses ``re.search`` so patterns can match anywhere in the output (not
just from the start).
"""

from __future__ import annotations

import re

from llmlint.checks import CheckResult
from llmlint.config import PatternCheckConfig


def run(config: PatternCheckConfig, output: str, **context: object) -> CheckResult:
    """Check *output* against required (``must_match``) and blocked (``must_not_match``) patterns."""
    for pattern in config.must_match:
        if not re.search(pattern, output):
            return CheckResult(
                name=config.name,
                check_type="pattern",
                severity=config.severity,
                detail=f"Required pattern not found: {pattern}",
            )

    for pattern in config.must_not_match:
        match = re.search(pattern, output)
        if match:
            return CheckResult(
                name=config.name,
                check_type="pattern",
                severity=config.severity,
                detail=f"Blocked pattern matched: {pattern} (found '{match.group()}')",
            )

    return CheckResult(name=config.name, check_type="pattern", severity="pass")
