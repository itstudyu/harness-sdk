# harness-gen plan (build-spec.md Section 4.5): .harness/plan/{yyyymmdd-작업명}/ 관리
"""
- plan list                                    : 모든 plan 디렉터리 (시간 역순)
- plan show <slug>                             : 특정 plan 의 plan.md / *-plan.md / status.yaml 출력
- plan clean --older-than=30d                  : 30일 이상 된 plan 삭제
- plan clean --status=abandoned                : 특정 상태 plan 삭제
- plan clean --status=done --older-than=7d     : 둘 다 매칭

자동 삭제 X (Karpathy 단순함). 사용자가 명시적으로 호출.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import click
import yaml

OLDER_THAN_RE = re.compile(r"^(\d+)d$")
VALID_STATUSES: frozenset[str] = frozenset(
    {"pending", "in_progress", "done", "failed", "abandoned"}
)


@click.group(name="plan")
def plan_group() -> None:
    """plan 디렉터리 관리 (`.harness/plan/`)."""


@plan_group.command(name="list")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
def plan_list(project_root: Path) -> None:
    """모든 plan 을 시간 역순으로 출력 (status 표시)."""
    plans = _scan_plans(project_root.resolve())
    if not plans:
        click.echo("(plan 없음)")
        return
    for slug, info in plans:
        status = info.get("status", "?")
        started = info.get("started_at", "")
        click.echo(f"  {slug}  [{status}]  {started}")


@plan_group.command(name="show")
@click.argument("slug")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
def plan_show(slug: str, project_root: Path) -> None:
    """slug 디렉터리의 모든 .md + status.yaml 출력."""
    plan_dir = project_root.resolve() / ".harness" / "plan" / slug
    if not plan_dir.is_dir():
        raise click.ClickException(f"plan 없음: {plan_dir}")
    for path in sorted(plan_dir.iterdir()):
        click.echo(f"\n=== {path.name} ===")
        click.echo(path.read_text(encoding="utf-8"))


@plan_group.command(name="clean")
@click.option("--older-than", default=None, help="예: 30d (30일 이상 된 plan 매칭).")
@click.option("--status", default=None, help="특정 status 매칭 (done/failed/abandoned 등).")
@click.option("--yes", is_flag=True, default=False, help="확인 prompt 건너뛰기.")
@click.option("--project-root", default=".", type=click.Path(file_okay=False, path_type=Path))
def plan_clean(
    older_than: str | None, status: str | None, yes: bool, project_root: Path
) -> None:
    """조건 매치 plan 디렉터리 삭제. --older-than/--status 중 최소 하나."""
    if not older_than and not status:
        raise click.ClickException("--older-than / --status 중 최소 하나 지정.")
    cutoff = _parse_cutoff(older_than) if older_than else None
    if status and status not in VALID_STATUSES:
        raise click.ClickException(f"--status 는 {sorted(VALID_STATUSES)} 중 하나.")
    targets = _select_for_cleanup(project_root.resolve(), cutoff=cutoff, status=status)
    if not targets:
        click.echo("매칭되는 plan 없음.")
        return
    _confirm_and_delete(targets, yes=yes)


def _scan_plans(project_root: Path) -> list[tuple[str, dict[str, Any]]]:
    """.harness/plan/ 안의 모든 plan 을 slug 역순 (yyyymmdd-... 이므로 = 시간 역순)."""
    root = project_root / ".harness" / "plan"
    if not root.is_dir():
        return []
    out: list[tuple[str, dict[str, Any]]] = []
    for entry in sorted(root.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        out.append((entry.name, _read_status(entry)))
    return out


def _read_status(plan_dir: Path) -> dict[str, Any]:
    status_path = plan_dir / "status.yaml"
    if not status_path.exists():
        return {}
    raw = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def _parse_cutoff(older_than: str) -> datetime:
    """--older-than=30d → 30일 전 cutoff datetime (UTC)."""
    m = OLDER_THAN_RE.match(older_than.strip())
    if not m:
        raise click.ClickException(f"--older-than 형식: '<N>d' (예: 30d). 받음: {older_than}")
    days = int(m.group(1))
    return datetime.now(timezone.utc) - timedelta(days=days)


def _select_for_cleanup(
    project_root: Path, *, cutoff: datetime | None, status: str | None
) -> list[Path]:
    plans = _scan_plans(project_root)
    selected: list[Path] = []
    base = project_root / ".harness" / "plan"
    for slug, info in plans:
        if status and info.get("status") != status:
            continue
        if cutoff and not _is_older_than(info, cutoff):
            continue
        selected.append(base / slug)
    return selected


def _is_older_than(info: dict[str, Any], cutoff: datetime) -> bool:
    started = info.get("started_at")
    if not isinstance(started, str):
        return False
    try:
        ts = datetime.fromisoformat(started.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts < cutoff


def _confirm_and_delete(targets: list[Path], *, yes: bool) -> None:
    click.echo(f"{len(targets)} 개 plan 삭제 예정:")
    for t in targets:
        click.echo(f"  - {t.name}")
    if not yes:
        if not click.confirm("계속?", default=False):
            click.echo("취소.")
            return
    for t in targets:
        shutil.rmtree(t)
    click.echo(f"✓ {len(targets)} 개 삭제됨.")
