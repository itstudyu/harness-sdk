# Stage 5 integration test: harness-gen verify exit code 분기
"""
build-spec.md Section 4.3:
- 0: OK
- 1: config <-> .harness/ 불일치
- 2: override 미승인
- 3: deprecated 룰 사용 중
"""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from click.testing import CliRunner

from cli.generate import generate_cmd
from cli.init import init_cmd
from cli.verify import EXIT_DEPRECATED, EXIT_MISMATCH, EXIT_UNAPPROVED, verify_cmd

PROJECT = Path(__file__).resolve().parents[2]


def _setup(workspace: Path, *, subagents: str = "") -> None:
    shutil.copytree(PROJECT / "reference" / "shared", workspace / "reference" / "shared")
    runner = CliRunner()
    runner.invoke(
        init_cmd,
        [
            "--registry", "local:reference/shared",
            "--domain", "payment", "--stack", "java-vertx",
            "--subagents", subagents,
            "--project-root", str(workspace),
            "--non-interactive",
        ],
    )
    runner.invoke(generate_cmd, ["--project-root", str(workspace)])


def test_verify_ok_after_fresh_generate(tmp_path: Path) -> None:
    _setup(tmp_path)
    runner = CliRunner()
    result = runner.invoke(verify_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_verify_missing_config_returns_mismatch(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(verify_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == EXIT_MISMATCH


def test_verify_mismatch_when_config_imports_changed(tmp_path: Path) -> None:
    _setup(tmp_path)
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["imports"] = ["shared@v9.9.9/rules/Rule_New"]  # generate 안 한 import
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(verify_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == EXIT_MISMATCH


def test_verify_unapproved_override(tmp_path: Path) -> None:
    _setup(tmp_path, subagents="frontend-agent")
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    # approved_by 없이 overrides 추가 → CI validator 가 먼저 잡지만, _check_unapproved 도 안전망
    cfg["agents"]["overrides"] = {"frontend-agent": {"framework": "angular@16"}}
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(verify_cmd, ["--project-root", str(tmp_path)])
    # validator 가 먼저 잡으면 MISMATCH (config 검증 실패 → return None → MISMATCH)
    # 안전망 _check_unapproved 까지 가면 UNAPPROVED
    assert result.exit_code in (EXIT_MISMATCH, EXIT_UNAPPROVED)


def test_verify_deprecated_rule(tmp_path: Path) -> None:
    _setup(tmp_path)
    # _resolved 디렉터리에 deprecated rule 수동 추가
    resolved = tmp_path / ".harness" / "rules" / "_resolved"
    resolved.mkdir(parents=True, exist_ok=True)
    (resolved / "Rule_Old.yaml").write_text(
        "id: Rule_Old\ndescription: old\nseverity: MAY\ndeprecated: true\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(verify_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == EXIT_DEPRECATED
    assert "Rule_Old" in result.output
