"""JSON parseability check with optional markdown fence stripping.

LLMs commonly wrap JSON in markdown code fences (````` ```json … ``` `````).
When ``strip_markdown_fences`` is enabled (the default), those fences are
removed before parsing.
"""

from __future__ import annotations

import json
import re

from llmlint.checks import CheckResult
from llmlint.config import JsonValidCheckConfig

_FENCE_PATTERN = re.compile(r"^```(?:json|JSON)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove surrounding markdown code fences if present."""
    text = text.strip()
    match = _FENCE_PATTERN.match(text)
    return match.group(1) if match else text


def run(config: JsonValidCheckConfig, output: str, **context: object) -> CheckResult:
    """Check that *output* is parseable JSON, optionally stripping markdown fences."""
    text = _strip_fences(output) if config.strip_markdown_fences else output

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
