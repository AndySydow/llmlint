"""YAML config loading and Pydantic models for check definitions.

Each check rule in a YAML file maps to a typed Pydantic model via a
discriminated union on the ``type`` field.  Example YAML::

    checks:
      - type: length
        name: not_too_long
        severity: warn
        max_chars: 10000

      - type: pattern
        name: no_pii
        must_not_match:
          - '\\d{3}-\\d{2}-\\d{4}'

The ``load_rules()`` function parses the file and returns a validated
list of config objects ready for the engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field


class BaseCheckConfig(BaseModel):
    """Fields shared by every check type.

    Attributes:
        name: Human-readable label shown in results and stored in the DB.
        severity: ``"fail"`` (default) for hard failures, ``"warn"`` for
            soft/advisory checks.
    """

    name: str
    severity: Literal["fail", "warn"] = "fail"


class SchemaCheckConfig(BaseCheckConfig):
    """Validate that JSON output conforms to a JSON Schema.

    Attributes:
        json_schema: A JSON Schema dict (any draft supported by the
            ``jsonschema`` library).
    """

    type: Literal["schema"]
    json_schema: dict


class LengthCheckConfig(BaseCheckConfig):
    """Enforce character and/or token length bounds.

    All bounds are optional — omit a field to skip that check.

    Attributes:
        min_chars: Minimum character count (inclusive).
        max_chars: Maximum character count (inclusive).
        min_tokens: Minimum token count (requires ``llmlint[tokens]``).
        max_tokens: Maximum token count (requires ``llmlint[tokens]``).
        tokenizer: ``tiktoken`` encoding name (default ``cl100k_base``).
    """

    type: Literal["length"]
    min_chars: int | None = None
    max_chars: int | None = None
    min_tokens: int | None = None
    max_tokens: int | None = None
    tokenizer: str = "cl100k_base"


class PatternCheckConfig(BaseCheckConfig):
    """Require or block regex patterns in output.

    Patterns use ``re.search`` — they can match anywhere in the output.

    Attributes:
        must_match: Patterns that must all be present (AND logic).
        must_not_match: Patterns that must all be absent (blocklist).
    """

    type: Literal["pattern"]
    must_match: list[str] = Field(default_factory=list)
    must_not_match: list[str] = Field(default_factory=list)


class JsonValidCheckConfig(BaseCheckConfig):
    """Check that the output is parseable JSON.

    Attributes:
        strip_markdown_fences: When ``True`` (default), strips
            surrounding ````` ``` ````` / ````` ```json ````` fences before parsing.
    """

    type: Literal["json_valid"]
    strip_markdown_fences: bool = True


class RefusalCheckConfig(BaseCheckConfig):
    """Detect LLM refusal via case-insensitive substring matching.

    Attributes:
        phrases: Substrings that indicate a refusal.  Defaults to common
            refusal phrases (``"I cannot"``, ``"As an AI"``, etc.).
        threshold: Number of distinct phrases that must match to trigger.
    """

    type: Literal["refusal"]
    phrases: list[str] = Field(
        default_factory=lambda: [
            "I cannot",
            "I'm unable",
            "I can't",
            "As an AI",
            "I'm sorry, but",
            "I apologize, but",
        ]
    )
    threshold: int = 1


# Discriminated union — Pydantic picks the right model based on ``type``.
CheckConfig = Annotated[
    SchemaCheckConfig | LengthCheckConfig | PatternCheckConfig | JsonValidCheckConfig | RefusalCheckConfig,
    Field(discriminator="type"),
]


class RulesFile(BaseModel):
    """Top-level structure of a ``checks.yaml`` file."""

    checks: list[CheckConfig]


def load_rules(path: str | Path) -> list[CheckConfig]:
    """Load and validate check rules from a YAML file.

    Args:
        path: Filesystem path to the YAML rules file.

    Returns:
        A list of typed check-config objects.

    Raises:
        FileNotFoundError: If *path* does not exist.
        pydantic.ValidationError: If the YAML content is invalid.
    """
    with open(path) as f:
        raw = yaml.safe_load(f)
    parsed = RulesFile.model_validate(raw)
    return parsed.checks
