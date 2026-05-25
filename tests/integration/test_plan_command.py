# Stage 7 integration test: harness-gen plan list/show/clean
"""
build-spec.md Section 4.5:
- plan list: 시간 역순
- plan show <slug>: 모든 파일 출력
- plan clean --older-than=Nd / --status=<S>: 매치된 디렉터리 삭제 (확인 prompt, --yes skip)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from click.testing import CliRunner

from cli.plan import plan_group


def _make_plan(
    project_root: Path,
    slug: str,
    *,
    status: str = "done",
    started: datetime | None = None,
    extra_files: dict[str, str] | None = None,
) -> Path:
    plan_dir = project_root / ".harness" / "plan" / slug
    plan_dir.mkdir(parents=True)
    iso = (started or datetime.now(timezone.utc)).isoformat()
    (plan_dir / "status.yaml").write_text(
        yaml.safe_dump({"task_slug": slug, "status": status, "started_at": iso}),
        encoding="utf-8",
    )
    (plan_dir / "plan.md").write_text(f"# {slug}\n\nworkflow.\n", encoding="utf-8")
    for name, body in (extra_files or {}).items():
        (plan_dir / name).write_text(body, encoding="utf-8")
    return plan_dir


def test_plan_list_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(plan_group, ["list", "--project-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "plan 없음" in result.output


def test_plan_list_reverse_chronological(tmp_path: Path) -> None:
    _make_plan(tmp_path, "20260520-old", status="done")
    _make_plan(tmp_path, "20260525-new", status="in_progress")
    runner = CliRunner()
    result = runner.invoke(plan_group, ["list", "--project-root", str(tmp_path)])
    assert result.exit_code == 0
    # 새것이 먼저
    new_idx = result.output.index("20260525-new")
    old_idx = result.output.index("20260520-old")
    assert new_idx < old_idx
    assert "[in_progress]" in result.output
    assert "[done]" in result.output


def test_plan_show_outputs_all_files(tmp_path: Path) -> None:
    _make_plan(
        tmp_path, "20260525-payment",
        extra_files={"frontend-plan.md": "## Frontend tasks\n"},
    )
    runner = CliRunner()
    result = runner.invoke(
        plan_group, ["show", "20260525-payment", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "plan.md" in result.output
    assert "frontend-plan.md" in result.output
    assert "status.yaml" in result.output


def test_plan_show_missing_slug_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        plan_group, ["show", "20260525-nope", "--project-root", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert "plan 없음" in result.output


def test_plan_clean_requires_at_least_one_filter(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(plan_group, ["clean", "--project-root", str(tmp_path)])
    assert result.exit_code != 0


def test_plan_clean_by_status(tmp_path: Path) -> None:
    _make_plan(tmp_path, "20260525-keep", status="in_progress")
    _make_plan(tmp_path, "20260525-bad", status="abandoned")
    runner = CliRunner()
    result = runner.invoke(
        plan_group,
        ["clean", "--status", "abandoned", "--yes", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert not (tmp_path / ".harness" / "plan" / "20260525-bad").exists()
    assert (tmp_path / ".harness" / "plan" / "20260525-keep").exists()


def test_plan_clean_by_older_than(tmp_path: Path) -> None:
    old_started = datetime.now(timezone.utc) - timedelta(days=40)
    _make_plan(tmp_path, "20260415-very-old", status="done", started=old_started)
    _make_plan(tmp_path, "20260524-recent", status="done")
    runner = CliRunner()
    result = runner.invoke(
        plan_group,
        ["clean", "--older-than", "30d", "--yes", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert not (tmp_path / ".harness" / "plan" / "20260415-very-old").exists()
    assert (tmp_path / ".harness" / "plan" / "20260524-recent").exists()


def test_plan_clean_combined_status_and_older_than(tmp_path: Path) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=10)
    _make_plan(tmp_path, "20260515-old-done", status="done", started=old)
    _make_plan(tmp_path, "20260515-old-failed", status="failed", started=old)
    runner = CliRunner()
    result = runner.invoke(
        plan_group,
        [
            "clean", "--status", "done", "--older-than", "7d", "--yes",
            "--project-root", str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert not (tmp_path / ".harness" / "plan" / "20260515-old-done").exists()
    assert (tmp_path / ".harness" / "plan" / "20260515-old-failed").exists()


def test_plan_clean_invalid_status_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        plan_group,
        ["clean", "--status", "garbage", "--yes", "--project-root", str(tmp_path)],
    )
    assert result.exit_code != 0


def test_plan_clean_invalid_older_than_format_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        plan_group,
        ["clean", "--older-than", "30days", "--yes", "--project-root", str(tmp_path)],
    )
    assert result.exit_code != 0
