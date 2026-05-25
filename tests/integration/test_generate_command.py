# Stage 4 integration test: harness-gen generate end-to-end (PoC local 모드)
"""
build-spec.md Section 4.2 Phase 1~9 의 전체 흐름을 reference/shared seed 로 검증.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from click.testing import CliRunner

from cli.generate import generate_cmd
from cli.init import init_cmd

PROJECT = Path(__file__).resolve().parents[2]


def _init_workspace(workspace: Path, *, subagents: str = "", tools: str = "") -> None:
    """reference/shared 를 workspace 안에 복사하고 init 실행 (PoC 모드)."""
    seed = workspace / "reference" / "shared"
    shutil.copytree(PROJECT / "reference" / "shared", seed)
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:reference/shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--subagents", subagents,
            "--tools", tools,
            "--project-root", str(workspace),
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output


def test_generate_minimal_no_imports(tmp_path: Path) -> None:
    """imports 빈 상태 + planner only — 가장 단순 케이스."""
    _init_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # 핵심 산출물 존재
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".claude" / "settings.json").exists()
    assert (tmp_path / ".claude" / "skills" / "planner" / "SKILL.md").exists()
    assert (tmp_path / ".harness" / ".lock.yaml").exists()
    assert (tmp_path / ".harness" / "agents" / "manifest.yaml").exists()
    # planner templates 도 복사됨
    assert (tmp_path / ".claude" / "skills" / "planner" / "templates" / "plan-multi.md.tmpl").exists()


def test_generate_with_subagent_does_not_auto_install_skills(tmp_path: Path) -> None:
    """frontend-agent 선택만 → Subagent 설치되지만 lint-checker 등 skill 은 자동 설치 X.

    정책: frontmatter 의 skills 는 비어있음. 사용자가 overrides 로 명시한 것만 설치.
    """
    _init_workspace(tmp_path, subagents="frontend-agent")
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # Subagent 자체는 설치
    assert (tmp_path / ".claude" / "agents" / "frontend-agent.md").exists()
    # lint-checker 는 자동 설치 X (사용자 명시 안 함)
    assert not (tmp_path / ".claude" / "skills" / "lint-checker").exists()
    # manifest 검증
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    assert manifest["agents"]["frontend-agent"]["install_kind"] == "subagent"
    assert "lint-checker" not in manifest["agents"]
    assert manifest["agents"]["planner"]["always_installed"] is True
    # CLAUDE.md 에 agent 목록 포함
    claude_md = (tmp_path / "CLAUDE.md").read_text()
    assert "frontend-agent" in claude_md
    assert "planner" in claude_md


def test_generate_user_can_opt_in_lint_checker_via_overrides(tmp_path: Path) -> None:
    """사용자가 overrides.skills 로 lint-checker 명시 → .claude/skills/lint-checker/ 설치."""
    _init_workspace(tmp_path, subagents="frontend-agent")
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["agents"]["overrides"] = {
        "frontend-agent": {
            "skills": ["lint-checker"],
            "approved_by": "@user",
            "approved_at": "2026-05-25",
        }
    }
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # 이번엔 설치됨
    assert (tmp_path / ".claude" / "skills" / "lint-checker" / "SKILL.md").exists()
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    assert "lint-checker" in manifest["agents"]
    assert "lint-checker" in manifest["agents"]["frontend-agent"]["skills_preloaded"]


def test_generate_with_tool_skill(tmp_path: Path) -> None:
    """code-analyst (non-isolation) 선택 → Skill 로 설치."""
    _init_workspace(tmp_path, tools="code-analyst")
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "skills" / "code-analyst" / "SKILL.md").exists()
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    assert manifest["agents"]["code-analyst"]["install_kind"] == "skill"


def test_generate_writes_session_start_hook(tmp_path: Path) -> None:
    """Section 9.5 — settings.json 에 SessionStart 훅."""
    _init_workspace(tmp_path)
    runner = CliRunner()
    runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    import json
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    hook = settings["hooks"]["SessionStart"][0]["hooks"][0]
    assert hook["type"] == "command"
    assert "harness-gen context" in hook["command"]


def test_generate_lockfile_has_registry_info(tmp_path: Path) -> None:
    _init_workspace(tmp_path, subagents="backend-agent")
    runner = CliRunner()
    runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    lock = yaml.safe_load((tmp_path / ".harness" / ".lock.yaml").read_text())
    assert lock["registry"] == "local:reference/shared"
    assert lock["registry_mode"] == "local"
    agent_names = {a["name"] for a in lock["agents"]}
    assert "planner" in agent_names
    assert "backend-agent" in agent_names


def test_generate_overrides_custom_field_into_manifest(tmp_path: Path) -> None:
    """agents.overrides 의 자유 필드 → manifest.custom."""
    _init_workspace(tmp_path, subagents="frontend-agent")
    # config 수정: overrides 추가
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["agents"]["overrides"] = {
        "frontend-agent": {
            "framework": "angular@16",
            "approved_by": "@kim",
            "approved_at": "2026-05-24",
        }
    }
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    custom = manifest["agents"]["frontend-agent"].get("custom") or {}
    assert custom.get("framework") == "angular@16"


def test_generate_fails_without_config(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code != 0
    assert "없음" in result.output or "harness-gen init" in result.output


def test_generate_wraps_fetcher_error_as_click_exception(tmp_path: Path) -> None:
    """존재하지 않는 agent 를 subagents 에 적으면 Python traceback 대신 친절한 에러."""
    _init_workspace(tmp_path, subagents="nonexistent-agent")
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code != 0
    # ClickException 은 "Error: <message>" 로 출력. traceback 키워드 X.
    assert "Traceback" not in result.output
    assert "nonexistent-agent" in result.output


def test_generate_local_skills_installed(tmp_path: Path) -> None:
    """HIGH 1: local.skills 가 .claude/skills/<X>/ 로 설치되고 manifest 에 등록."""
    _init_workspace(tmp_path)
    skill_dir = tmp_path / "local" / "skills" / "my-validator"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-validator\ndescription: 프로젝트 전용 검증 도구.\n---\n# my-validator\n",
        encoding="utf-8",
    )
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["local"] = {"skills": ["local/skills/my-validator"]}
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "skills" / "my-validator" / "SKILL.md").exists()
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    assert "my-validator" in manifest["agents"]
    assert manifest["agents"]["my-validator"]["install_kind"] == "skill"


def test_generate_subagent_falls_back_to_agents_local(tmp_path: Path) -> None:
    """HIGH 2: subagents: 에 이름만 적었는데 shared 에 없으면 agents.local 에서 매칭."""
    _init_workspace(tmp_path)
    local_agent = tmp_path / "local" / "agents" / "mobile-agent.md"
    local_agent.parent.mkdir(parents=True)
    local_agent.write_text(
        "---\nname: mobile-agent\ndescription: Mobile 전용 격리 agent.\n"
        "tools: [Read, Write]\n---\n# Mobile Agent\n",
        encoding="utf-8",
    )
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["agents"]["subagents"] = ["mobile-agent"]
    cfg["agents"]["local"] = ["local/agents/mobile-agent.md"]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "agents" / "mobile-agent.md").exists()
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    assert manifest["agents"]["mobile-agent"]["install_kind"] == "subagent"
    # 중복 설치 없어야 함 — manifest 에 mobile-agent 가 단 1번만
    assert sum(1 for k in manifest["agents"] if k == "mobile-agent") == 1


def test_generate_local_rule_id_conflict_raises(tmp_path: Path) -> None:
    """HIGH 3: local rule id 가 imports 한 rule id 와 충돌 → ClickException."""
    _init_workspace(tmp_path)
    # imports 에 reference seed 의 어떤 rule 도 없으므로, 인위적으로 id 충돌 시나리오 만들기 위해
    # local rule 2개를 같은 id 로 작성 (local 내부 중복 충돌도 검출하는지 함께 검증)
    local_dir = tmp_path / "local" / "rules"
    local_dir.mkdir(parents=True)
    (local_dir / "a.yaml").write_text("id: Rule_Same\nseverity: error\n", encoding="utf-8")
    (local_dir / "b.yaml").write_text("id: Rule_Same\nseverity: warn\n", encoding="utf-8")
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["local"] = {"rules": ["local/rules/a.yaml", "local/rules/b.yaml"]}
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code != 0
    assert "Rule_Same" in result.output
    assert "Traceback" not in result.output


def test_generate_lockfile_has_registry_commit_field(tmp_path: Path) -> None:
    """HIGH 4: lockfile entry 에 commit 필드 (local 모드는 null)."""
    _init_workspace(tmp_path)
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    lock = yaml.safe_load((tmp_path / ".harness" / ".lock.yaml").read_text())
    # 새 필드 존재 (local 모드는 None)
    assert "registry_commit" in lock
    assert lock["registry_commit"] is None


def test_generate_claude_md_marker_includes_install_kind_for_planner(tmp_path: Path) -> None:
    """MEDIUM 5: CLAUDE.md planner 라인이 '(always, skill)' 패턴."""
    _init_workspace(tmp_path)
    runner = CliRunner()
    runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    claude_md = (tmp_path / "CLAUDE.md").read_text()
    assert "**planner** (always, skill)" in claude_md


def test_generate_overrides_skill_append_installs_dependency(tmp_path: Path) -> None:
    """agents.overrides.<X>.skills 로 append 한 skill 도 실제로 .claude/skills/ 에 설치되어야 함.

    HIGH 2 회귀 방지: install 순서 (overrides 적용 → 의존성 해결) 검증.
    """
    _init_workspace(tmp_path, subagents="frontend-agent")
    # registry seed 에 추가 skill 만들어두기 (preset 외 skill)
    extra_skill_dir = tmp_path / "reference" / "shared" / "skills" / "extra-helper"
    extra_skill_dir.mkdir(parents=True)
    (extra_skill_dir / "SKILL.md").write_text(
        "---\nname: extra-helper\ndescription: 테스트용 추가 도구.\n---\n# Extra Helper\n",
        encoding="utf-8",
    )
    # config 에 overrides.skills append
    cfg_path = tmp_path / ".harness-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["agents"]["overrides"] = {
        "frontend-agent": {
            "skills": ["extra-helper"],
            "approved_by": "@kim",
            "approved_at": "2026-05-25",
        }
    }
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    runner = CliRunner()
    result = runner.invoke(generate_cmd, ["--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    # append 된 skill 의 SKILL.md 가 실제로 설치되어야 함
    assert (tmp_path / ".claude" / "skills" / "extra-helper" / "SKILL.md").exists()
    manifest = yaml.safe_load((tmp_path / ".harness" / "agents" / "manifest.yaml").read_text())
    assert "extra-helper" in manifest["agents"]
    assert "extra-helper" in manifest["agents"]["frontend-agent"]["skills_preloaded"]
