# harness-gen verify (build-spec.md Section 4.3): CI 동기화 검증, exit code 분기
"""
검증 항목:
- config 검증 (CI 모드)
- .harness/.lock.yaml 의 imports 가 현재 config 의 imports 와 일치하는지 (동기화)
- agents.overrides.<X>.approved_by 누락 (CI 모드면 schema validator 가 이미 잡음)
- _resolved/ 노드 중 deprecated: true 인 것 사용 중인지

Exit codes:
- 0: OK
- 1: config <-> .harness/ 불일치 (재 generate 필요)
- 2: override 미승인
- 3: deprecated 룰 사용
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml

from validators import load_and_validate

EXIT_OK = 0
EXIT_MISMATCH = 1
EXIT_UNAPPROVED = 2
EXIT_DEPRECATED = 3


@click.command(name="verify")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
def verify_cmd(project_root: Path) -> None:
    """`.harness/.lock.yaml` 과 config 동기화 + override 승인 + deprecated 체크."""
    project_root = project_root.resolve()
    exit_code = _verify(project_root)
    raise SystemExit(exit_code)


def _verify(project_root: Path) -> int:
    cfg = _read_or_fail(project_root)
    if cfg is None:
        return EXIT_MISMATCH
    code = _check_unapproved(cfg)
    if code != EXIT_OK:
        return code
    code = _check_lock_sync(project_root, cfg)
    if code != EXIT_OK:
        return code
    return _check_deprecated(project_root)


def _read_or_fail(project_root: Path) -> dict[str, Any] | None:
    """config 가 있고 CI-mode validator 를 통과하면 dict 반환. 실패 시 None + 에러 출력."""
    config_path = project_root / ".harness-config.yaml"
    if not config_path.exists():
        click.echo(f"⚠ {config_path} 없음 — 먼저 'harness-gen init + generate' 실행.", err=True)
        return None
    result = load_and_validate(config_path, ci_mode=True)
    if not result.ok:
        click.echo("config 검증 실패:", err=True)
        for e in result.errors:
            click.echo(f"  - {e}", err=True)
        return None
    return result.config


def _check_unapproved(config: dict[str, Any]) -> int:
    """agents.overrides 의 approved_by 누락 검사. CI validator 가 잡지만 안전망."""
    overrides = (config.get("agents") or {}).get("overrides") or {}
    unapproved = [k for k, v in overrides.items() if not (isinstance(v, dict) and v.get("approved_by"))]
    if unapproved:
        click.echo(f"override 미승인: {', '.join(unapproved)}", err=True)
        return EXIT_UNAPPROVED
    return EXIT_OK


def _check_lock_sync(project_root: Path, config: dict[str, Any]) -> int:
    """config 의 imports 가 .harness/.lock.yaml 의 imports.raw 와 정확히 일치하는지."""
    lock_path = project_root / ".harness" / ".lock.yaml"
    if not lock_path.exists():
        click.echo(f"{lock_path} 없음 — 'harness-gen generate' 필요.", err=True)
        return EXIT_MISMATCH
    lock = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
    locked = sorted(_extract_locked_imports(lock))
    declared = sorted(config.get("imports") or [])
    if locked != declared:
        click.echo(
            "config 의 imports 와 .lock.yaml 불일치:\n"
            f"  config:   {declared}\n"
            f"  lockfile: {locked}\n"
            "→ 'harness-gen generate' 재실행 필요.",
            err=True,
        )
        return EXIT_MISMATCH
    return EXIT_OK


def _extract_locked_imports(lock: dict[str, Any]) -> list[str]:
    entries = lock.get("imports") or []
    out: list[str] = []
    for e in entries:
        raw = e.get("raw") if isinstance(e, dict) else None
        if isinstance(raw, str):
            out.append(raw)
    return out


def _check_deprecated(project_root: Path) -> int:
    """.harness/rules/_resolved/*.yaml 중 deprecated: true 가 있으면 EXIT_DEPRECATED."""
    resolved_dir = project_root / ".harness" / "rules" / "_resolved"
    if not resolved_dir.exists():
        return EXIT_OK
    bad: list[str] = []
    for path in resolved_dir.glob("*.yaml"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("deprecated") is True:
            bad.append(raw.get("id", path.stem))
    if bad:
        click.echo(f"deprecated 룰 사용 중: {', '.join(bad)}", err=True)
        return EXIT_DEPRECATED
    return EXIT_OK
