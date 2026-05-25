# .harness-config.yaml 스키마 검증 (build-spec.md Section 5.1, 5.2)
"""
.harness-config.yaml 스키마 검증 (build-spec.md Section 5.1, 5.2)

Stage 1: 파싱 + 필드 검증만 담당.
agent 존재 검증 (shared/local 매칭) 은 Stage 4 Phase 2 후 단계에서 수행.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# 현재 지원하는 config schema 버전
SUPPORTED_VERSIONS: set[str] = {"1.0"}

# imports 형식: shared@<version>/<path>
IMPORT_PATTERN = re.compile(r"^shared@[^/]+/.+$")

# 필수 최상위 필드
REQUIRED_FIELDS: tuple[str, ...] = ("version", "domain", "stack", "registry")


@dataclass
class ConfigValidationError(Exception):
    """검증 실패. 메시지에 어떤 필드/이유인지 명시."""
    message: str

    def __str__(self) -> str:  # pragma: no cover (단순 위임)
        return self.message


@dataclass
class ConfigValidationResult:
    """검증 결과. errors 가 비어 있으면 OK."""
    config: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_and_validate(path: Path, ci_mode: bool = False) -> ConfigValidationResult:
    """파일 경로에서 config 를 읽어 검증.

    ci_mode=True 면 overrides.approved_by 누락이 error, 아니면 warning.
    """
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        return ConfigValidationResult(
            config={},
            errors=[f"config 최상위는 map 이어야 함 (실제: {type(data).__name__})"],
        )
    return validate_config(data, ci_mode=ci_mode)


def validate_config(config: dict[str, Any], ci_mode: bool = False) -> ConfigValidationResult:
    """이미 파싱된 dict 를 검증."""
    result = ConfigValidationResult(config=config)
    _check_required(config, result.errors)
    if "version" in config:
        _check_version(config["version"], result.errors)
    _check_imports(config.get("imports", []), result.errors)
    _check_local(config.get("local"), result.errors)
    _check_agents(config.get("agents", {}), ci_mode=ci_mode, result=result)
    return result


def _check_local(local: Any, errors: list[str]) -> None:
    """local: { rules, patterns, skills } — Section 5.1."""
    if local is None:
        return
    if not isinstance(local, dict):
        errors.append(f"'local' 는 map 이어야 함 (실제: {type(local).__name__})")
        return
    for fld in ("rules", "patterns", "skills"):
        _check_string_list(local.get(fld), f"local.{fld}", errors)


def _check_required(config: dict[str, Any], errors: list[str]) -> None:
    for fld in REQUIRED_FIELDS:
        if fld not in config:
            errors.append(f"필수 필드 누락: '{fld}'")
        elif not isinstance(config[fld], str) or not config[fld]:
            errors.append(f"'{fld}' 는 비어있지 않은 문자열이어야 함")


def _check_version(version: Any, errors: list[str]) -> None:
    if not isinstance(version, str):
        errors.append(f"'version' 은 문자열이어야 함 (실제: {type(version).__name__})")
        return
    if version not in SUPPORTED_VERSIONS:
        errors.append(
            f"지원하지 않는 schema 버전: '{version}' (지원: {sorted(SUPPORTED_VERSIONS)})"
        )


def _check_imports(imports: Any, errors: list[str]) -> None:
    if imports is None:
        return
    if not isinstance(imports, list):
        errors.append(f"'imports' 는 list 여야 함 (실제: {type(imports).__name__})")
        return
    for idx, item in enumerate(imports):
        if not isinstance(item, str):
            errors.append(f"imports[{idx}] 는 문자열이어야 함")
            continue
        if not IMPORT_PATTERN.match(item):
            errors.append(
                f"imports[{idx}] 형식 위반: '{item}' "
                f"(기대: 'shared@<version>/<path>')"
            )


def _check_agents(agents: Any, ci_mode: bool, result: ConfigValidationResult) -> None:
    if agents is None:
        return
    if not isinstance(agents, dict):
        result.errors.append(f"'agents' 는 map 이어야 함 (실제: {type(agents).__name__})")
        return

    _check_string_list(agents.get("subagents"), "agents.subagents", result.errors)
    _check_tools(agents.get("tools"), result)
    _check_string_list(agents.get("local"), "agents.local", result.errors)
    _check_overrides(agents.get("overrides"), ci_mode=ci_mode, result=result)


def _check_tools(tools: Any, result: ConfigValidationResult) -> None:
    """tools 는 string list. 'planner' 가 명시되면 warning + config 에서 제거."""
    if tools is None:
        return
    _check_string_list(tools, "agents.tools", result.errors)
    if not isinstance(tools, list):
        return
    if "planner" in tools:
        result.warnings.append(
            "agents.tools 에 'planner' 명시됨 — planner 는 항상 자동 설치이므로 제거함"
        )
        # config 자체에서도 제거 (이후 stage 가 이 값을 참고)
        result.config["agents"]["tools"] = [t for t in tools if t != "planner"]


def _check_string_list(value: Any, field_name: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"'{field_name}' 는 list 여야 함 (실제: {type(value).__name__})")
        return
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{field_name}[{idx}] 는 비어있지 않은 문자열이어야 함")


def _check_overrides(overrides: Any, ci_mode: bool, result: ConfigValidationResult) -> None:
    """agents.overrides 전용 approved_by 검증 (build-spec.md Section 5.2).

    rules-level overrides 의 approved_by 검증은 Stage 4 (generate Phase 4) 의
    resolver/overrides.py 책임 — 거기서 import 된 rule 실체와 매칭한 뒤 검증.
    Stage 1 (schema 파싱) 은 agents.overrides 만 처리.
    """
    if overrides is None:
        return
    if not isinstance(overrides, dict):
        result.errors.append(
            f"'agents.overrides' 는 map 이어야 함 (실제: {type(overrides).__name__})"
        )
        return
    for key, override in overrides.items():
        if not isinstance(override, dict):
            result.errors.append(
                f"agents.overrides.{key} 는 map 이어야 함 (실제: {type(override).__name__})"
            )
            continue
        approved_by = override.get("approved_by")
        if not approved_by or not isinstance(approved_by, str):
            msg = f"agents.overrides.{key}.approved_by 누락 (사람의 명시적 승인 필요)"
            if ci_mode:
                result.errors.append(msg)
            else:
                result.warnings.append(msg)
