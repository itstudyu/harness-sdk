# harness-gen CLI 통합 entry point (pyproject [project.scripts] 가 가리킴)
"""
build-spec.md Section 4 의 모든 subcommand 를 한 click group 에 등록.

Stage 별 점진 등록:
- Stage 3: init
- Stage 4: generate
- Stage 5: verify
- Stage 6: update
- Stage 7: plan
- Stage 8: context
"""
from __future__ import annotations

import click

from cli.generate import generate_cmd
from cli.init import init_cmd
from cli.verify import verify_cmd


@click.group(name="harness-gen")
@click.version_option(version="0.1.0", prog_name="harness-gen")
def cli() -> None:
    """harness-gen: multi-agent 오케스트레이션 CLI scaffold."""


cli.add_command(init_cmd)
cli.add_command(generate_cmd)
cli.add_command(verify_cmd)


if __name__ == "__main__":
    cli()
