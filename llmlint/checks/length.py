"""Character and token length bounds check.

Character counting is always available.  Token counting requires the
optional ``tiktoken`` dependency (install via ``llmlint[tokens]``).
"""

from __future__ import annotations

from llmlint.checks import CheckResult
from llmlint.config import LengthCheckConfig


def run(config: LengthCheckConfig, output: str, **context: object) -> CheckResult:
    """Check that *output* length is within the configured character/token bounds."""
    char_count = len(output)

    if config.min_chars is not None and char_count < config.min_chars:
        return CheckResult(
            name=config.name,
            check_type="length",
            severity=config.severity,
            detail=f"Too short: {char_count} chars < min {config.min_chars}",
        )

    if config.max_chars is not None and char_count > config.max_chars:
        return CheckResult(
            name=config.name,
            check_type="length",
            severity=config.severity,
            detail=f"Too long: {char_count} chars > max {config.max_chars}",
        )

    if config.min_tokens is not None or config.max_tokens is not None:
        try:
            import tiktoken
        except ImportError:
            return CheckResult(
                name=config.name,
                check_type="length",
                severity="fail",
                detail="Install llmlint[tokens] for token counting",
            )

        enc = tiktoken.get_encoding(config.tokenizer)
        token_count = len(enc.encode(output))

        if config.min_tokens is not None and token_count < config.min_tokens:
            return CheckResult(
                name=config.name,
                check_type="length",
                severity=config.severity,
                detail=f"Too few tokens: {token_count} < min {config.min_tokens}",
            )

        if config.max_tokens is not None and token_count > config.max_tokens:
            return CheckResult(
                name=config.name,
                check_type="length",
                severity=config.severity,
                detail=f"Too many tokens: {token_count} > max {config.max_tokens}",
            )

    return CheckResult(name=config.name, check_type="length", severity="pass")
