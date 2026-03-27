# llmlint

Declarative quality checks for LLM outputs in production. Define rules in YAML. Catch regressions before your users do.

Like pytest, but for AI.

[![PyPI version](https://img.shields.io/pypi/v/llmlint)](https://pypi.org/project/llmlint/)
[![Python](https://img.shields.io/pypi/pyversions/llmlint)](https://pypi.org/project/llmlint/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why llmlint?

LLM outputs are non-deterministic. A prompt that works today can silently regress tomorrow — longer responses, leaked PII, broken JSON, unexpected refusals. **llmlint** validates every output against your rules, automatically, with zero latency impact.

- **Declarative** — define checks in YAML, not code
- **Non-blocking** — checks run in background threads, never slowing your responses
- **Provider-agnostic** — works with OpenAI, Anthropic, local models, anything that produces text
- **Lightweight** — under 2,000 lines of core code, pip-installable, no platform lock-in

## Installation

```bash
pip install llmlint
```

With optional extras:

```bash
pip install llmlint[tokens]      # tiktoken for token counting
pip install llmlint[postgres]    # PostgreSQL storage backend
pip install llmlint[all]         # everything
```

## Quick Start

### 1. Define your rules

Create a `checks.yaml` file:

```yaml
checks:
  - type: json_valid
    name: output_is_valid_json
    severity: fail

  - type: schema
    name: response_schema
    severity: fail
    json_schema:
      type: object
      required: [answer, confidence]
      properties:
        answer:
          type: string
        confidence:
          type: number
          minimum: 0
          maximum: 1

  - type: length
    name: not_too_long
    severity: warn
    max_chars: 10000

  - type: pattern
    name: no_pii
    severity: fail
    must_not_match:
      - '\b\d{3}-\d{2}-\d{4}\b'  # SSN
      - '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'  # email

  - type: refusal
    name: detect_refusal
    severity: warn
```

### 2. Use in your code

```python
import llmlint

# Initialize with your rules and a storage backend
llmlint.init(
    rules_path="checks.yaml",
    store_url="sqlite:///llmlint.db",
)

# Option A: Inline check — get results back
result = llmlint.check(llm_output)

if result.has_failures:
    print(f"Check failed: {result.failures}")

# Option B: Decorator — fire-and-forget, zero latency
@llmlint.watch()
def ask_llm(prompt: str) -> str:
    response = openai.chat.completions.create(...)
    return response.choices[0].message.content
```

## Usage Modes

### `check()` — Inline

Run checks and get results back synchronously. Use when you need to inspect or act on failures.

```python
result = llmlint.check(output, model="gpt-4", meta={"user_id": "abc"})

result.has_failures  # bool
result.failures      # list of failed checks
result.warnings      # list of warnings
result.results       # all check results
```

### `@watch()` — Decorator

Wrap any function that returns LLM output. Checks run in background threads after the function returns — zero latency added to the response path.

```python
@llmlint.watch(model="gpt-4")
def generate_response(prompt: str) -> str:
    return call_llm(prompt)

# Returns immediately, checks run in background
response = generate_response("Hello")
```

### `load()` — Validate Rules

Parse and validate a rules file without running any checks. Useful for CI or debugging.

```python
rules = llmlint.load("checks.yaml")
print(f"Loaded {len(rules)} checks")
```

## Check Types

| Type | Key | What It Does |
|------|-----|-------------|
| **JSON Valid** | `json_valid` | Validates JSON parseability, strips markdown fences |
| **Schema** | `schema` | Validates against a JSON Schema |
| **Length** | `length` | Enforces min/max character or token bounds |
| **Pattern** | `pattern` | Regex matching — require or block patterns (PII, citations) |
| **Refusal** | `refusal` | Detects refusal phrases ("I cannot", "As an AI") |

### Severity Levels

- **`fail`** (default) — hard failure, should trigger alerts
- **`warn`** — soft failure, logged but not critical
- **`pass`** — check passed

## Check Reference

### `json_valid`

```yaml
- type: json_valid
  name: output_is_json
  strip_markdown_fences: true  # default: true
```

### `schema`

```yaml
- type: schema
  name: api_response
  json_schema:
    type: object
    required: [answer]
    properties:
      answer:
        type: string
```

### `length`

```yaml
- type: length
  name: not_too_short
  min_chars: 20
  max_chars: 10000
  # Token counting requires: pip install llmlint[tokens]
  min_tokens: 10
  max_tokens: 2000
  tokenizer: cl100k_base  # default
```

### `pattern`

```yaml
- type: pattern
  name: no_pii
  must_match:          # ALL must match (fail if any missing)
    - '\[citation\]'
  must_not_match:      # NONE may match (fail if any found)
    - '\b\d{3}-\d{2}-\d{4}\b'
```

### `refusal`

```yaml
- type: refusal
  name: detect_refusal
  threshold: 1  # number of phrase matches to trigger
  phrases:      # defaults provided if omitted
    - "I cannot"
    - "I'm unable"
    - "As an AI"
```

## Storage

Check results are persisted for analysis and debugging. Pass a connection string to `init()`:

```python
# SQLite (default, great for local dev)
llmlint.init(store_url="sqlite:///llmlint.db")

# PostgreSQL (production) — requires: pip install llmlint[postgres]
llmlint.init(store_url="postgresql://user:pass@host/db")
```

Each result records: check name, type, severity, output hash, model, latency, failure detail, and arbitrary metadata.

## Development

```bash
# Setup
git clone https://github.com/derdatenarchitekt/llmlint.git
cd llmlint
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=llmlint --cov-report=term-missing

# Lint & format
uv run ruff check .
uv run ruff format .
```

## License

MIT
