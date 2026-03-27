"""YAML config loading and pydantic models for check definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field


class BaseCheckConfig(BaseModel):
    """Base config shared by all check types."""

    name: str
    severity: Literal["fail", "warn"] = "fail"


class SchemaCheckConfig(BaseCheckConfig):
    type: Literal["schema"]
    json_schema: dict


class LengthCheckConfig(BaseCheckConfig):
    type: Literal["length"]
    min_chars: int | None = None
    max_chars: int | None = None
    min_tokens: int | None = None
    max_tokens: int | None = None
    tokenizer: str = "cl100k_base"


class PatternCheckConfig(BaseCheckConfig):
    type: Literal["pattern"]
    must_match: list[str] = Field(default_factory=list)
    must_not_match: list[str] = Field(default_factory=list)


class JsonValidCheckConfig(BaseCheckConfig):
    type: Literal["json_valid"]
    strip_markdown_fences: bool = True


class RefusalCheckConfig(BaseCheckConfig):
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


CheckConfig = Annotated[
    SchemaCheckConfig | LengthCheckConfig | PatternCheckConfig | JsonValidCheckConfig | RefusalCheckConfig,
    Field(discriminator="type"),
]


class RulesFile(BaseModel):
    checks: list[CheckConfig]


def load_rules(path: str | Path) -> list[CheckConfig]:
    """Load and validate check rules from a YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    parsed = RulesFile.model_validate(raw)
    return parsed.checks
