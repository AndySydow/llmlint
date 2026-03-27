"""JSON Schema validation check.

Parses the output as JSON, then validates it against the user-supplied
JSON Schema using the ``jsonschema`` library.
"""

from __future__ import annotations

import json

import jsonschema

from llmlint.checks import CheckResult
from llmlint.config import SchemaCheckConfig


def run(config: SchemaCheckConfig, output: str, **context: object) -> CheckResult:
    """Validate that *output* is valid JSON conforming to *config.json_schema*."""
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError) as e:
        return CheckResult(
            name=config.name,
            check_type="schema",
            severity=config.severity,
            detail=f"Output is not valid JSON: {e}",
        )

    try:
        jsonschema.validate(instance=data, schema=config.json_schema)
    except jsonschema.ValidationError as e:
        return CheckResult(
            name=config.name,
            check_type="schema",
            severity=config.severity,
            detail=f"Schema validation failed: {e.message}",
        )

    return CheckResult(name=config.name, check_type="schema", severity="pass")
