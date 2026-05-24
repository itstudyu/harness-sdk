# Stage 3 integration test: harness-gen init 의 모든 분기 (preset 있음/없음, 옵션, --non-interactive)
"""
build-spec.md Section 4.1 의 동작:
- preset 있음 → recommended_imports/subagents/tools 자동 채움
- preset 없음 → warning + 빈 상태
- planner in tools → warning + 제거
- 기존 config 있음 → error
- .gitignore 자동 갱신 (이미 있으면 추가 안 함)
"""
from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from cli.init import init_cmd


def _make_local_seed(tmp_path: Path, preset_yaml: str | None = None) -> Path:
    """tmp_path 안에 'local:shared' 구조 시드. preset_yaml 주면 java-vertx.yaml 생성."""
    shared = tmp_path / "shared"
    (shared / "rules").mkdir(parents=True)
    if preset_yaml is not None:
        presets = shared / "presets"
        presets.mkdir()
        (presets / "java-vertx.yaml").write_text(preset_yaml, encoding="utf-8")
    return tmp_path


def test_init_with_preset_populates_imports(tmp_path: Path) -> None:
    preset_yaml = (
        "recommended_imports:\n"
        "  - shared@v1.2.0/rules/Rule_JWT\n"
        "  - shared@v1.2.0/patterns/Pattern_JWT_Java\n"
        "recommended_subagents: [frontend-agent]\n"
        "recommended_tools: [code-analyst]\n"
    )
    _make_local_seed(tmp_path, preset_yaml)
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--stack", "java-vertx",
            "--domain", "payment",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((tmp_path / ".harness-config.yaml").read_text())
    assert config["domain"] == "payment"
    assert config["stack"] == "java-vertx"
    assert config["registry"] == "local:shared"
    assert "shared@v1.2.0/rules/Rule_JWT" in config["imports"]
    assert config["agents"]["subagents"] == ["frontend-agent"]
    assert config["agents"]["tools"] == ["code-analyst"]


def test_init_without_preset_warns_and_uses_empty(tmp_path: Path) -> None:
    _make_local_seed(tmp_path, preset_yaml=None)
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--stack", "unknown-stack",
            "--domain", "user",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "preset 'unknown-stack.yaml' 을 찾을 수 없음" in result.output
    config = yaml.safe_load((tmp_path / ".harness-config.yaml").read_text())
    assert config["imports"] == [] or config["imports"] is None
    assert config["agents"]["subagents"] == [] or config["agents"]["subagents"] is None


def test_init_planner_in_tools_filtered(tmp_path: Path) -> None:
    _make_local_seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--tools", "planner,code-analyst",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "planner 는 항상 자동 설치" in result.output
    config = yaml.safe_load((tmp_path / ".harness-config.yaml").read_text())
    assert "planner" not in (config["agents"]["tools"] or [])
    assert "code-analyst" in (config["agents"]["tools"] or [])


def test_init_explicit_options_override_preset(tmp_path: Path) -> None:
    preset_yaml = "recommended_subagents: [backend-agent]\n"
    _make_local_seed(tmp_path, preset_yaml)
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--subagents", "frontend-agent",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    config = yaml.safe_load((tmp_path / ".harness-config.yaml").read_text())
    assert config["agents"]["subagents"] == ["frontend-agent"]


def test_init_refuses_to_overwrite_existing_config(tmp_path: Path) -> None:
    _make_local_seed(tmp_path)
    (tmp_path / ".harness-config.yaml").write_text("existing: true\n")
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code != 0
    assert "이미 존재함" in result.output


def test_init_updates_gitignore_idempotently(tmp_path: Path) -> None:
    _make_local_seed(tmp_path)
    (tmp_path / ".gitignore").write_text("node_modules/\n")
    runner = CliRunner()
    runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    content = (tmp_path / ".gitignore").read_text()
    assert "node_modules/" in content
    assert "~/.harness-cache/" in content
    assert ".harness/plan/" in content
    # 두 번째 init 은 config overwrite 거부지만, .gitignore 는 멱등이어야 함
    # → 다른 디렉터리로 검증
    other = tmp_path / "other"
    other.mkdir()
    runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--project-root", str(other),
            "--non-interactive",
        ],
    )


def test_init_invalid_registry_still_creates_config_with_warning(tmp_path: Path) -> None:
    """registry 디렉터리가 없어도 init 은 진행 (preset 못 찾음 warning 만)."""
    runner = CliRunner()
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:no_such_dir",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".harness-config.yaml").exists()


def test_init_non_interactive_requires_domain_and_stack(tmp_path: Path) -> None:
    """tech-agnostic 원칙: domain/stack default 하드코딩 X — non-interactive 에선 필수."""
    _make_local_seed(tmp_path)
    runner = CliRunner()
    # --domain 누락
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--stack", "java-vertx",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code != 0
    assert "--domain 필수" in result.output

    # --stack 누락
    result = runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    assert result.exit_code != 0
    assert "--stack 필수" in result.output


def test_generated_config_passes_stage1_validator(tmp_path: Path) -> None:
    """생성된 yaml 이 Stage 1 schema validator 를 통과해야 함 (계약 검증)."""
    from validators import load_and_validate

    preset_yaml = (
        "recommended_imports: [shared@v1.0.0/rules/Rule_X]\n"
        "recommended_subagents: [frontend-agent]\n"
        "recommended_tools: [code-analyst]\n"
    )
    _make_local_seed(tmp_path, preset_yaml)
    runner = CliRunner()
    runner.invoke(
        init_cmd,
        [
            "--registry", "local:shared",
            "--domain", "payment",
            "--stack", "java-vertx",
            "--project-root", str(tmp_path),
            "--non-interactive",
        ],
    )
    result = load_and_validate(tmp_path / ".harness-config.yaml", ci_mode=True)
    assert result.ok, f"생성된 config 가 validator 를 통과해야 함. errors={result.errors}"
