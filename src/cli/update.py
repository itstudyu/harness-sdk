# harness-gen update (build-spec.md Section 4.4): imports 버전 일괄 갱신 (config 만)
"""
config 의 imports 의 version 부분만 in-place 변경. 실제 fetch/.harness 재생성은 generate 책임.

- --to=<version>: 모든 import 의 version 을 강제 교체
- --minor / --major: SemVer bump (vMAJOR.MINOR.PATCH 형식만 지원, 비SemVer 는 warning + skip)
"""
from __future__ import annotations

import re
from pathlib import Path

import click

from registry import parse_import

# SemVer (선택적 v prefix): v1.2.3 또는 1.2.3
SEMVER_RE = re.compile(r"^(v)?(\d+)\.(\d+)\.(\d+)$")


@click.command(name="update")
@click.option("--to", "to_version", default=None, help="모든 import 의 version 을 이 값으로.")
@click.option("--minor", is_flag=True, default=False, help="SemVer minor +1, patch 0.")
@click.option("--major", is_flag=True, default=False, help="SemVer major +1, minor/patch 0.")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
def update_cmd(to_version: str | None, minor: bool, major: bool, project_root: Path) -> None:
    """`.harness-config.yaml` 의 imports 버전 일괄 갱신."""
    mode_count = sum([bool(to_version), minor, major])
    if mode_count != 1:
        raise click.ClickException("--to / --minor / --major 중 정확히 하나 지정.")
    project_root = project_root.resolve()
    config_path = project_root / ".harness-config.yaml"
    if not config_path.exists():
        raise click.ClickException(f"{config_path} 없음.")
    original = config_path.read_text(encoding="utf-8")
    updated, changed, skipped = _bump_imports(
        original, to_version=to_version, minor=minor, major=major
    )
    config_path.write_text(updated, encoding="utf-8")
    _report(changed, skipped, config_path)


def _bump_imports(
    text: str, *, to_version: str | None, minor: bool, major: bool
) -> tuple[str, list[tuple[str, str]], list[str]]:
    """yaml text 의 imports 라인만 정규식으로 in-place 교체 (yaml 라이브러리 X — 주석 보존)."""
    changed: list[tuple[str, str]] = []
    skipped: list[str] = []
    new_lines: list[str] = []
    for line in text.splitlines():
        new_line, kind = _try_bump_line(line, to_version=to_version, minor=minor, major=major)
        if kind == "changed":
            changed.append((line.strip(), new_line.strip()))
        elif kind == "skipped":
            skipped.append(line.strip())
        new_lines.append(new_line)
    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), changed, skipped


def _try_bump_line(
    line: str, *, to_version: str | None, minor: bool, major: bool
) -> tuple[str, str]:
    """yaml list entry (예: `  - shared@v1.2.0/rules/Rule_JWT`) 만 bump. 그 외 그대로."""
    stripped = line.lstrip()
    if not stripped.startswith("- shared@"):
        return line, "unchanged"
    indent = line[: len(line) - len(stripped)]
    item = stripped[2:].strip()
    try:
        ref = parse_import(item)
    except Exception:
        return line, "unchanged"
    new_version = _next_version(ref.version, to_version=to_version, minor=minor, major=major)
    if new_version is None:
        return line, "skipped"
    new_item = f"shared@{new_version}/{ref.path}"
    return f"{indent}- {new_item}", "changed"


def _next_version(
    current: str, *, to_version: str | None, minor: bool, major: bool
) -> str | None:
    if to_version:
        return to_version
    m = SEMVER_RE.match(current)
    if not m:
        return None
    prefix = m.group(1) or ""
    maj, mn, pat = int(m.group(2)), int(m.group(3)), int(m.group(4))
    if major:
        return f"{prefix}{maj + 1}.0.0"
    if minor:
        return f"{prefix}{maj}.{mn + 1}.0"
    return None


def _report(
    changed: list[tuple[str, str]], skipped: list[str], config_path: Path
) -> None:
    if changed:
        click.echo(f"✓ {len(changed)} 개 import version 갱신 ({config_path}):")
        for before, after in changed:
            click.echo(f"  - {before}")
            click.echo(f"  + {after}")
    if skipped:
        click.echo(f"⚠ {len(skipped)} 개 import 가 SemVer 형식 아님 — skip:", err=True)
        for line in skipped:
            click.echo(f"  - {line}", err=True)
    if not changed and not skipped:
        click.echo("변경 사항 없음 (imports 비어있거나 형식 다름).")
    click.echo("다음 단계: 'harness-gen generate' 로 실제 fetch + 재컴파일.")
