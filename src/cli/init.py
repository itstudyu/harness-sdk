# harness-gen init — .harness-config.yaml 템플릿 생성 (build-spec.md Section 4.1)
"""
동작 (Section 4.1):
1. preset (registry 의 reference/shared/presets/<stack>.yaml) 시도 — 없으면 warning + 빈 imports
2. 옵션 (--subagents, --tools) 으로 agent 선택 (planner 는 자동 포함, 명시 X)
3. .harness-config.yaml 템플릿 작성
4. .gitignore 에 ~/.harness-cache/ + .harness/plan/ 추가
5. 대화형 모드: 옵션 미지정 시 prompt

핵심: init 은 "참조 명시" 만. 실제 fetch/생성은 generate (Stage 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import click
import yaml

from registry import FetcherError, create_registry

CONFIG_FILENAME = ".harness-config.yaml"
GITIGNORE_FILENAME = ".gitignore"
GITIGNORE_ENTRIES: tuple[str, ...] = (
    "~/.harness-cache/",
    ".harness/plan/",
)


@dataclass
class PresetData:
    """preset yaml 의 추천 값들 (없을 수도 있음)."""
    imports: list[str] = field(default_factory=list)
    subagents: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    found: bool = False


@click.command(name="init")
@click.option("--stack", default=None, help="기술 스택 (예: java-vertx). preset 식별용.")
@click.option("--domain", default=None, help="도메인 (예: payment).")
@click.option(
    "--registry",
    default="local:reference/shared",
    show_default=True,
    help="공유 registry. 'local:<path>' (PoC) 또는 'bitbucket.../harness.git' (운용).",
)
@click.option(
    "--subagents",
    default="",
    help="설치할 Subagent 콤마 구분 (예: frontend-agent,backend-agent).",
)
@click.option(
    "--tools",
    default="",
    help="설치할 도구 skill 콤마 구분 (planner 는 자동, 명시 시 무시됨).",
)
@click.option(
    "--project-root",
    default=".",
    type=click.Path(file_okay=False, path_type=Path),
    help="대상 프로젝트 루트 (기본: 현재 디렉터리).",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="대화형 prompt 건너뛰기 (CI 용).",
)
def init_cmd(
    stack: str | None,
    domain: str | None,
    registry: str,
    subagents: str,
    tools: str,
    project_root: Path,
    non_interactive: bool,
) -> None:
    """프로젝트에 .harness-config.yaml 템플릿 생성."""
    project_root = project_root.resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    registry, domain, stack = _resolve_inputs(
        registry, domain, stack, non_interactive=non_interactive
    )
    preset = _load_preset_or_warn(registry, stack, project_root=project_root)
    chosen_subagents = _csv(subagents) or preset.subagents
    chosen_tools = _filter_planner(_csv(tools) or preset.tools)
    _write_config_or_fail(
        project_root,
        domain=domain, stack=stack, registry=registry,
        imports=preset.imports,
        subagents=chosen_subagents, tools=chosen_tools,
    )
    _ensure_gitignore(project_root)
    _echo_success(project_root)


def _write_config_or_fail(
    project_root: Path,
    *, domain: str, stack: str, registry: str,
    imports: list[str], subagents: list[str], tools: list[str],
) -> None:
    config_path = project_root / CONFIG_FILENAME
    if config_path.exists():
        raise click.ClickException(
            f"이미 존재함: {config_path}. 덮어쓰려면 직접 삭제 후 재실행."
        )
    config_path.write_text(
        _render_config(
            domain=domain, stack=stack, registry=registry,
            imports=imports, subagents=subagents, tools=tools,
        ),
        encoding="utf-8",
    )


def _echo_success(project_root: Path) -> None:
    click.echo(f"✓ 생성: {project_root / CONFIG_FILENAME}")
    click.echo(f"✓ .gitignore 갱신: {project_root / GITIGNORE_FILENAME}")
    click.echo("다음 단계: 편집 후 'harness-gen generate' 실행.")


def _resolve_inputs(
    registry: str, domain: str | None, stack: str | None, *, non_interactive: bool
) -> tuple[str, str, str]:
    """대화형/non-interactive 양쪽 입력 정규화.

    domain 은 자유 텍스트라 default 없으면 prompt 필수.
    stack 도 tech-agnostic 원칙상 default 하드코딩 금지 (AI-HANDOFF MUST NOT).
    non-interactive 에서 둘 다 필수 — 누락 시 ClickException.
    """
    if non_interactive:
        if not domain:
            raise click.ClickException("--domain 필수 (--non-interactive 모드).")
        if not stack:
            raise click.ClickException("--stack 필수 (--non-interactive 모드).")
        return registry, domain, stack
    registry = click.prompt("Registry URL", default=registry, show_default=True)
    domain_prompt = domain if domain else None
    stack_prompt = stack if stack else None
    domain = click.prompt("Domain", default=domain_prompt, show_default=bool(domain_prompt))
    stack = click.prompt("Stack", default=stack_prompt, show_default=bool(stack_prompt))
    return registry, domain, stack


def _load_preset_or_warn(registry: str, stack: str, *, project_root: Path) -> "PresetData":
    preset = _load_preset(registry, stack, project_root=project_root)
    if not preset.found:
        click.echo(
            f"⚠ preset '{stack}.yaml' 을 찾을 수 없음 — imports/subagents/tools 빈 상태로 생성. "
            "필요한 항목은 직접 채우세요.",
            err=True,
        )
    return preset


def _csv(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _filter_planner(tools: list[str]) -> list[str]:
    """planner 는 항상 자동 — 명시되면 warning + 제거."""
    if "planner" in tools:
        click.echo("ℹ planner 는 항상 자동 설치 — tools 목록에서 제거함.", err=True)
        return [t for t in tools if t != "planner"]
    return tools


def _load_preset(registry: str, stack: str, *, project_root: Path) -> PresetData:
    """registry 에서 presets/<stack>.yaml 시도. 없으면 found=False."""
    preset_path = _preset_path(registry, stack, project_root=project_root)
    if preset_path is None or not preset_path.exists():
        return PresetData()
    raw = yaml.safe_load(preset_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return PresetData()
    return PresetData(
        imports=list(raw.get("recommended_imports") or []),
        subagents=list(raw.get("recommended_subagents") or []),
        tools=list(raw.get("recommended_tools") or []),
        found=True,
    )


def _preset_path(registry: str, stack: str, *, project_root: Path) -> Path | None:
    """registry 가 유효하면 presets/<stack>.yaml 경로, 무효면 None."""
    try:
        reg = create_registry(registry, project_root=project_root)
    except FetcherError:
        return None
    return reg.root / "presets" / f"{stack}.yaml"


# `.harness-config.yaml` 템플릿 — string.Template 으로 간단 치환
_CONFIG_TEMPLATE = """\
version: "1.0"
domain: "{domain}"
stack: "{stack}"
registry: "{registry}"

# 공유 레지스트리에서 가져올 룰/패턴 (preset 추천값으로 시작)
imports:
{imports_block}

# 가져온 룰의 부분 수정 (필요할 때만, approved_by 필수)
overrides: {{}}

# 프로젝트 전용 룰/패턴 (공유에 없는 것)
local:
  rules: []
  patterns: []

# Agent 선택 (planner 는 항상 자동 설치, 명시 불필요)
agents:
  subagents:
{subagents_block}
  tools:
{tools_block}
  overrides: {{}}
  local: []
"""


def _render_config(
    *,
    domain: str, stack: str, registry: str,
    imports: list[str], subagents: list[str], tools: list[str],
) -> str:
    """`.harness-config.yaml` 템플릿 렌더링."""
    return _CONFIG_TEMPLATE.format(
        domain=domain, stack=stack, registry=registry,
        imports_block="\n".join(_yaml_list_or_empty(
            imports, indent="  ", example="# 예: - shared@v1.2.0/rules/Rule_JWT"
        )),
        subagents_block="\n".join(_yaml_list_or_empty(subagents, indent="    ")),
        tools_block="\n".join(_yaml_list_or_empty(tools, indent="    ")),
    )


def _yaml_list_or_empty(items: list[str], *, indent: str, example: str | None = None) -> list[str]:
    """list 가 있으면 yaml entry, 비어 있으면 '[]' (+ 예시 주석)."""
    if items:
        return [f"{indent}- {item}" for item in items]
    out: list[str] = []
    if example:
        out.append(f"{indent}{example}")
    out.append(f"{indent}[]")
    return out


def _ensure_gitignore(project_root: Path) -> None:
    """없으면 생성, 있으면 빠진 entry 만 append."""
    path = project_root / GITIGNORE_FILENAME
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    existing_lines = {ln.strip() for ln in existing.splitlines()}
    to_add = [entry for entry in GITIGNORE_ENTRIES if entry not in existing_lines]
    if not to_add:
        return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    block = prefix + "\n# harness-gen\n" + "\n".join(to_add) + "\n"
    with path.open("a", encoding="utf-8") as fp:
        fp.write(block)
