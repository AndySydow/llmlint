"""JSON parseability check with markdown fence stripping."""

from __future__ import annotations

import json
import re

from llmlint.checks import CheckResult
from llmlint.config import JsonValidCheckConfig

_FENCE_PATTERN = re.compile(r"^```(?:json|JSON)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Strip markdown code fences from text."""
    text = text.strip()
    match = _FENCE_PATTERN.match(text)
    if match:
        return match.group(1)
    return text


def run(config: JsonValidCheckConfig, output: str, **context: object) -> CheckResult:
    """Check that output is valid JSON, optionally stripping markdown fences."""
    text = output
    if config.strip_markdown_fences:
        text = _strip_fences(text)

    try:
        json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        return CheckResult(
            name=config.name,
            check_type="json_valid",
            severity=config.severity,
            detail=f"Invalid JSON: {e}",
        )

    return CheckResult(name=config.name, check_type="json_valid", severity="pass")
