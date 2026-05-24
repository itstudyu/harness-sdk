# Stage 1 integration test: .harness-config.yaml 파싱 + 검증 시나리오
"""
build-spec.md Section 5.1, 5.2 의 모든 검증 룰을 fixture 로 검증.

명세 우선 검증:
- required 누락 → error
- imports 형식 위반 → error
- agents.tools 에 planner → warning + 제거
- overrides.approved_by 누락 → warning (개발) / error (CI)
"""
from pathlib import Path

from validators import load_and_validate

FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_minimal_config_passes() -> None:
    result = load_and_validate(FIXTURES / "valid_minimal.yaml")
    assert result.ok, f"valid_minimal 가 통과해야 함. errors={result.errors}"
    assert result.warnings == []


def test_valid_full_config_passes() -> None:
    result = load_and_validate(FIXTURES / "valid_full.yaml")
    assert result.ok, f"valid_full 가 통과해야 함. errors={result.errors}"


def test_missing_required_fields_fail() -> None:
    result = load_and_validate(FIXTURES / "invalid_missing_required.yaml")
    assert not result.ok
    joined = " | ".join(result.errors)
    assert "stack" in joined
    assert "registry" in joined


def test_invalid_import_format_fails() -> None:
    result = load_and_validate(FIXTURES / "invalid_import_format.yaml")
    assert not result.ok
    assert any("imports[0]" in e for e in result.errors), result.errors


def test_planner_in_tools_warns_and_removed() -> None:
    result = load_and_validate(FIXTURES / "warn_planner_in_tools.yaml")
    assert result.ok, f"planner 명시는 warning 만 (error X). errors={result.errors}"
    assert any("planner" in w for w in result.warnings)
    assert "planner" not in result.config["agents"]["tools"]
    assert "code-analyst" in result.config["agents"]["tools"]


def test_missing_approved_by_dev_mode_is_warning() -> None:
    result = load_and_validate(FIXTURES / "missing_approved_by.yaml", ci_mode=False)
    assert result.ok, f"개발 모드에선 warning. errors={result.errors}"
    assert any("approved_by" in w for w in result.warnings)


def test_missing_approved_by_ci_mode_is_error() -> None:
    result = load_and_validate(FIXTURES / "missing_approved_by.yaml", ci_mode=True)
    assert not result.ok
    assert any("approved_by" in e for e in result.errors)
