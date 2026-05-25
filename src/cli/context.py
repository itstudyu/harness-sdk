# harness-gen context (build-spec.md Section 4.6 + 9.5): SessionStart 훅이 호출
"""
동작:
1. 프로젝트 루트의 CLAUDE.md 읽기
2. .harness/.lock.yaml 의 generated_at 확인 (1시간 초과 시 stale 경고)
3. stdout 으로 (경고 + CLAUDE.md) 출력 — Claude Code 가 자동 캡처
4. Exit 0 보장 (그래야 컨텍스트에 추가됨)

stderr 는 디버그용 (Claude Code 컨텍스트 미반영).
빠른 실행 (≤500ms 권장) — yaml 파싱은 작은 lock 파일만.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click
import yaml

STALE_THRESHOLD = timedelta(hours=1)


@click.command(name="context")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
@click.option("--light", is_flag=True, default=False,
              help="lightweight 모드 (lock 체크만, CLAUDE.md 본문 생략 — UserPromptSubmit 훅 용).")
def context_cmd(project_root: Path, light: bool) -> None:
    """SessionStart 훅이 호출. stdout 으로 CLAUDE.md + stale 경고."""
    project_root = project_root.resolve()
    warning = _stale_warning(project_root)
    if warning:
        click.echo(warning)
    if not light:
        body = _claude_md_text(project_root)
        if body is not None:
            click.echo(body)
    # 항상 Exit 0 — Claude Code 가 stdout 을 컨텍스트에 추가하려면 성공 종료 필수.


def _claude_md_text(project_root: Path) -> str | None:
    """루트 CLAUDE.md 본문 반환. 없으면 None (stderr 안내)."""
    path = project_root / "CLAUDE.md"
    if not path.exists():
        click.echo(
            f"⚠ {path} 없음 — 'harness-gen generate' 후 사용하세요.", err=True
        )
        return None
    return path.read_text(encoding="utf-8")


def _stale_warning(project_root: Path) -> str | None:
    """lock 의 generated_at 이 STALE_THRESHOLD 초과 시 경고 문자열, 아니면 None."""
    lock_path = project_root / ".harness" / ".lock.yaml"
    if not lock_path.exists():
        return None
    raw = yaml.safe_load(lock_path.read_text(encoding="utf-8")) or {}
    ts = _parse_generated_at(raw)
    if ts is None:
        return None
    age = datetime.now(timezone.utc) - ts
    if age <= STALE_THRESHOLD:
        return None
    return (
        f"⚠ 이 프로젝트의 harness 컨텍스트가 {_humanize(age)} 전에 생성됨.\n"
        "  최신 룰 적용 위해 `harness-gen generate` 권장.\n"
    )


def _parse_generated_at(lock: dict[str, Any]) -> datetime | None:
    raw = lock.get("generated_at")
    if not isinstance(raw, str):
        return None
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _humanize(age: timedelta) -> str:
    """대략적인 사람 친화 표현 (정밀도 X)."""
    days = age.days
    if days >= 1:
        return f"{days}일"
    hours = age.seconds // 3600
    if hours >= 1:
        return f"{hours}시간"
    minutes = age.seconds // 60
    return f"{minutes}분"
