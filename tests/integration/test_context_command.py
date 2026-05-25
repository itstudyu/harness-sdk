# Stage 8 integration test: harness-gen context (SessionStart 훅)
"""
build-spec.md Section 4.6 + 9.5:
- stdout 으로 CLAUDE.md 본문 출력
- .lock.yaml 의 generated_at 이 1시간 초과 시 stdout 상단에 경고
- Exit 0 보장 (CLAUDE.md 없어도 — Claude Code 가 컨텍스트로 추가하려면 성공 종료)
- --light 모드: 본문 생략, stale 체크만
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from click.testing import CliRunner

from cli.context import context_cmd


def _write_lock(project_root: Path, generated_at: datetime) -> None:
    lock = project_root / ".harness" / ".lock.yaml"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        yaml.safe_dump({"version": "1.0", "generated_at": generated_at.isoformat()}),
        encoding="utf-8",
    )


def _write_claude_md(project_root: Path, body: str) -> None:
    (project_root / "CLAUDE.md").write_text(body, encoding="utf-8")


def test_context_outputs_claude_md(tmp_path: Path) -> None:
    _write_claude_md(tmp_path, "# Project Context\n\n룰 X 적용.\n")
    _write_lock(tmp_path, datetime.now(timezone.utc))
    runner = CliRunner()
    result = runner.invoke(context_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "# Project Context" in result.output
    assert "룰 X 적용" in result.output
    # 갓 생성 → stale 경고 X
    assert "권장" not in result.output


def test_context_warns_when_stale(tmp_path: Path) -> None:
    _write_claude_md(tmp_path, "# stale project\n")
    old = datetime.now(timezone.utc) - timedelta(days=2)
    _write_lock(tmp_path, old)
    runner = CliRunner()
    result = runner.invoke(context_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "harness 컨텍스트" in result.output
    assert "harness-gen generate" in result.output
    # 본문도 같이
    assert "# stale project" in result.output


def test_context_no_lock_no_warning(tmp_path: Path) -> None:
    """lock 없으면 stale 체크 skip (warning X). 본문은 그대로 출력."""
    _write_claude_md(tmp_path, "# fresh\n")
    runner = CliRunner()
    result = runner.invoke(context_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "권장" not in result.output
    assert "# fresh" in result.output


def test_context_missing_claude_md_still_exit_zero(tmp_path: Path) -> None:
    """CLAUDE.md 없어도 Exit 0 — 안내는 stderr 로."""
    runner = CliRunner()
    result = runner.invoke(context_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0
    # CliRunner 의 output 은 stdout+stderr 통합 (mix_stderr=True default)
    assert "없음" in result.output or "generate" in result.output


def test_context_light_mode_skips_body(tmp_path: Path) -> None:
    _write_claude_md(tmp_path, "# full body\n")
    _write_lock(tmp_path, datetime.now(timezone.utc) - timedelta(days=3))
    runner = CliRunner()
    result = runner.invoke(context_cmd, ["--light", "--project-root", str(tmp_path)])
    assert result.exit_code == 0
    # stale 경고는 출력
    assert "권장" in result.output
    # 본문은 출력 안 됨
    assert "# full body" not in result.output


def test_context_humanizes_age(tmp_path: Path) -> None:
    """경고 메시지에 '일' 또는 '시간' 단위가 포함되는지."""
    _write_claude_md(tmp_path, "# x\n")
    _write_lock(tmp_path, datetime.now(timezone.utc) - timedelta(hours=5))
    runner = CliRunner()
    result = runner.invoke(context_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "5시간" in result.output or "시간" in result.output
