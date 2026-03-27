"""llmlint CLI entry point."""

from __future__ import annotations

import click

from llmlint import __name__ as pkg_name


@click.group()
@click.version_option(package_name=pkg_name)
def main() -> None:
    """llmlint — Declarative quality checks for LLM outputs."""


if __name__ == "__main__":
    main()
